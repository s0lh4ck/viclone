import os
import secrets
import shutil
import uuid

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from vclone import audio, auth, config, db, rvc_engine, voice_engine
from vclone.logging_setup import logger

app = Flask(__name__)

if config.SECRET_KEY:
    app.secret_key = config.SECRET_KEY
else:
    app.secret_key = secrets.token_hex(32)
    logger.warning(
        "VICLONE_SECRET_KEY is not set -- using a random key generated at startup. "
        "Sessions will not survive a restart. Set VICLONE_SECRET_KEY in production."
    )

if not auth.is_auth_configured():
    logger.warning(
        "VICLONE_PASSWORD is not set -- the app is running WITHOUT a login gate. "
        "Do not use this against real client material until authentication is configured."
    )

app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

db.init_db()


def case_dir(case_id, sub):
    path = os.path.join(config.STORAGE_DIR, str(case_id), sub)
    os.makedirs(path, exist_ok=True)
    return path


def get_case_or_404(conn, case_id):
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        abort(404)
    return case


@app.before_request
def enforce_auth():
    if not auth.is_auth_configured():
        return None
    if request.endpoint in ("login", "static") or request.endpoint is None:
        return None
    if not session.get("authenticated"):
        return redirect(url_for("login", next=request.path))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if not auth.is_auth_configured():
        return redirect(url_for("index"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if auth.check_password(password):
            session.clear()
            session["authenticated"] = True
            session.permanent = True
            next_url = request.form.get("next") or url_for("index")
            return redirect(next_url)
        logger.warning("Failed login attempt")
        flash("Incorrect password.", "error")

    return render_template("login.html", next=request.args.get("next", ""))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    with db.get_conn() as conn:
        cases = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    return render_template("index.html", cases=cases)


@app.route("/cases", methods=["POST"])
def create_case():
    name = request.form.get("name", "").strip()
    client = request.form.get("client", "").strip()
    target_person = request.form.get("target_person", "").strip()
    authorization_ref = request.form.get("authorization_ref", "").strip()

    if not all([name, client, target_person, authorization_ref]):
        flash(
            "All fields are required, including the authorization reference.",
            "error",
        )
        return redirect(url_for("index"))

    with db.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO cases (name, client, target_person, authorization_ref) "
            "VALUES (?, ?, ?, ?)",
            (name, client, target_person, authorization_ref),
        )
        case_id = cur.lastrowid

    logger.info("Case %s created (client=%r, target=%r)", case_id, client, target_person)
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<int:case_id>")
def case_detail(case_id):
    with db.get_conn() as conn:
        case = get_case_or_404(conn, case_id)
        references = conn.execute(
            "SELECT * FROM reference_files WHERE case_id = ? ORDER BY uploaded_at DESC",
            (case_id,),
        ).fetchall()
        outputs = conn.execute(
            "SELECT * FROM generated_outputs WHERE case_id = ? ORDER BY created_at DESC",
            (case_id,),
        ).fetchall()

    model_dir = case_dir(case_id, "voice_model")
    model_status = rvc_engine.training_status(case_id, model_dir)
    live_running = rvc_engine.live_status(case_id)

    return render_template(
        "case_detail.html",
        case=case,
        references=references,
        outputs=outputs,
        model_status=model_status,
        live_running=live_running,
        live_engine_implemented=config.LIVE_ENGINE_IMPLEMENTED,
    )


@app.route("/cases/<int:case_id>/upload", methods=["POST"])
def upload_reference(case_id):
    with db.get_conn() as conn:
        case = get_case_or_404(conn, case_id)

    if case["closed_at"]:
        flash("This case is closed. Reopen a new case to add material.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    file = request.files.get("reference_file")
    if not file or file.filename == "":
        flash("Select an audio or video file.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    if not audio.is_allowed_filename(file.filename):
        flash("Unsupported file format.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    raw_dir = case_dir(case_id, "raw")
    ref_dir = case_dir(case_id, "reference")

    raw_name = f"{uuid.uuid4().hex}_{file.filename}"
    raw_path = os.path.join(raw_dir, raw_name)
    file.save(raw_path)

    try:
        wav_name = audio.process_reference_upload(raw_path, ref_dir, file.filename)
    except audio.AudioProcessingError as exc:
        logger.error("Case %s: reference processing failed: %s", case_id, exc)
        flash(f"Error processing the file: {exc}", "error")
        return redirect(url_for("case_detail", case_id=case_id))
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO reference_files (case_id, filename, relative_path) "
            "VALUES (?, ?, ?)",
            (case_id, file.filename, os.path.join("reference", wav_name)),
        )

    logger.info("Case %s: reference sample %r uploaded", case_id, file.filename)
    flash("Voice sample processed successfully.", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<int:case_id>/generate", methods=["POST"])
def generate_speech(case_id):
    with db.get_conn() as conn:
        case = get_case_or_404(conn, case_id)
        references = conn.execute(
            "SELECT * FROM reference_files WHERE case_id = ?", (case_id,)
        ).fetchall()

    if case["closed_at"]:
        flash("This case is closed.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    if not references:
        flash("Upload at least one voice sample before generating audio.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    text = request.form.get("text", "").strip()
    language = request.form.get("language", config.DEFAULT_LANGUAGE).strip() or (
        config.DEFAULT_LANGUAGE
    )

    if not text:
        flash("Enter the text to synthesize.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    ref_paths = [
        os.path.join(config.STORAGE_DIR, str(case_id), r["relative_path"])
        for r in references
    ]

    out_dir = case_dir(case_id, "generated")
    out_name = f"{uuid.uuid4().hex}.wav"
    out_path = os.path.join(out_dir, out_name)

    try:
        voice_engine.synthesize(text, ref_paths, language, out_path)
    except Exception as exc:  # the model/torch stack can raise many exception types
        logger.exception("Case %s: speech generation failed", case_id)
        flash(f"Error generating audio: {exc}", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO generated_outputs (case_id, text, language, relative_path) "
            "VALUES (?, ?, ?, ?)",
            (case_id, text, language, os.path.join("generated", out_name)),
        )

    logger.info("Case %s: generated scripted audio (%d chars, lang=%s)", case_id, len(text), language)
    flash("Audio generated.", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<int:case_id>/train", methods=["POST"])
def train_voice_model(case_id):
    with db.get_conn() as conn:
        case = get_case_or_404(conn, case_id)
        references = conn.execute(
            "SELECT * FROM reference_files WHERE case_id = ?", (case_id,)
        ).fetchall()

    if case["closed_at"]:
        flash("This case is closed.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    if not references:
        flash("Upload at least one voice sample before training a model.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    ref_dir = case_dir(case_id, "reference")
    model_dir = case_dir(case_id, "voice_model")

    try:
        rvc_engine.start_training(case_id, ref_dir, model_dir)
        logger.info("Case %s: voice model training started", case_id)
        flash("Training started. Check the training log for progress.", "success")
    except RuntimeError as exc:
        flash(str(exc), "error")

    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<int:case_id>/train/status")
def train_status(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
    model_dir = case_dir(case_id, "voice_model")
    return jsonify({"status": rvc_engine.training_status(case_id, model_dir)})


@app.route("/devices")
def devices():
    try:
        inputs, outputs = rvc_engine.list_audio_devices()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"inputs": inputs, "outputs": outputs})


@app.route("/cases/<int:case_id>/live/start", methods=["POST"])
def live_start(case_id):
    with db.get_conn() as conn:
        case = get_case_or_404(conn, case_id)

    if case["closed_at"]:
        return jsonify({"error": "This case is closed."}), 400

    model_dir = case_dir(case_id, "voice_model")
    if rvc_engine.training_status(case_id, model_dir) != "ready":
        return jsonify({"error": "No trained voice model for this case yet."}), 400

    data = request.get_json(force=True, silent=True) or {}
    try:
        input_device = int(data.get("input_device"))
        output_device = int(data.get("output_device"))
    except (TypeError, ValueError):
        return jsonify({"error": "Select an input and output device."}), 400
    pitch = float(data.get("pitch", 0.0) or 0.0)

    try:
        rvc_engine.start_live_conversion(case_id, model_dir, input_device, output_device, pitch)
        logger.info(
            "Case %s: live conversion started (in=%s out=%s pitch=%s)",
            case_id, input_device, output_device, pitch,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"running": True})


@app.route("/cases/<int:case_id>/live/stop", methods=["POST"])
def live_stop(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
    rvc_engine.stop_live_conversion(case_id)
    logger.info("Case %s: live conversion stopped", case_id)
    return jsonify({"running": False})


@app.route("/cases/<int:case_id>/live/status")
def live_status_route(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
    return jsonify({"running": rvc_engine.live_status(case_id)})


@app.route("/cases/<int:case_id>/close", methods=["POST"])
def close_case(case_id):
    with db.get_conn() as conn:
        case = get_case_or_404(conn, case_id)

    if case["closed_at"]:
        flash("This case is already closed.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    confirm_name = request.form.get("confirm_name", "").strip()
    if confirm_name != case["name"]:
        flash("Case name confirmation did not match. Nothing was deleted.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    rvc_engine.stop_live_conversion(case_id)

    case_path = os.path.join(config.STORAGE_DIR, str(case_id))
    if os.path.exists(case_path):
        shutil.rmtree(case_path)

    with db.get_conn() as conn:
        conn.execute("UPDATE cases SET closed_at = datetime('now') WHERE id = ?", (case_id,))
        conn.execute("DELETE FROM reference_files WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM generated_outputs WHERE case_id = ?", (case_id,))

    logger.info("Case %s closed: all stored voice material deleted", case_id)
    flash("Case closed. All stored voice material has been deleted.", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/storage/<int:case_id>/<path:relative_path>")
def serve_storage(case_id, relative_path):
    directory = os.path.join(config.STORAGE_DIR, str(case_id))
    return send_from_directory(directory, relative_path)


@app.errorhandler(413)
def too_large(_exc):
    flash(f"File too large (max {config.MAX_UPLOAD_MB} MB).", "error")
    return redirect(request.referrer or url_for("index"))


@app.errorhandler(404)
def not_found(_exc):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(exc):
    logger.exception("Unhandled server error: %s", exc)
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
