import os
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
    url_for,
)

from vclone import audio, config, db, rvc_engine, voice_engine

app = Flask(__name__)
app.secret_key = os.environ.get("VICLONE_SECRET_KEY", "dev-only-change-me")

db.init_db()


def case_dir(case_id, sub):
    path = os.path.join(config.STORAGE_DIR, str(case_id), sub)
    os.makedirs(path, exist_ok=True)
    return path


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[-1].lower() in config.ALLOWED_REFERENCE_EXTENSIONS
    )


def get_case_or_404(conn, case_id):
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        abort(404)
    return case


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
    )


@app.route("/cases/<int:case_id>/upload", methods=["POST"])
def upload_reference(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)

    file = request.files.get("reference_file")
    if not file or file.filename == "":
        flash("Select an audio or video file.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    if not allowed_file(file.filename):
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

    flash("Voice sample processed successfully.", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<int:case_id>/generate", methods=["POST"])
def generate_speech(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
        references = conn.execute(
            "SELECT * FROM reference_files WHERE case_id = ?", (case_id,)
        ).fetchall()

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
        flash(f"Error generating audio: {exc}", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO generated_outputs (case_id, text, language, relative_path) "
            "VALUES (?, ?, ?, ?)",
            (case_id, text, language, os.path.join("generated", out_name)),
        )

    flash("Audio generated.", "success")
    return redirect(url_for("case_detail", case_id=case_id))


@app.route("/cases/<int:case_id>/train", methods=["POST"])
def train_voice_model(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
        references = conn.execute(
            "SELECT * FROM reference_files WHERE case_id = ?", (case_id,)
        ).fetchall()

    if not references:
        flash("Upload at least one voice sample before training a model.", "error")
        return redirect(url_for("case_detail", case_id=case_id))

    ref_dir = case_dir(case_id, "reference")
    model_dir = case_dir(case_id, "voice_model")

    try:
        rvc_engine.start_training(case_id, ref_dir, model_dir)
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
        get_case_or_404(conn, case_id)

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
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"running": True})


@app.route("/cases/<int:case_id>/live/stop", methods=["POST"])
def live_stop(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
    rvc_engine.stop_live_conversion(case_id)
    return jsonify({"running": False})


@app.route("/cases/<int:case_id>/live/status")
def live_status_route(case_id):
    with db.get_conn() as conn:
        get_case_or_404(conn, case_id)
    return jsonify({"running": rvc_engine.live_status(case_id)})


@app.route("/storage/<int:case_id>/<path:relative_path>")
def serve_storage(case_id, relative_path):
    directory = os.path.join(config.STORAGE_DIR, str(case_id))
    return send_from_directory(directory, relative_path)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
