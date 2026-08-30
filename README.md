# ViClone

Herramienta interna para equipos de auditoría de seguridad: convierte muestras de voz
(audio o vídeo) de una persona **dentro del alcance autorizado de un ejercicio de vishing**
en un modelo de voz clonada, que luego se usa para generar frases sintetizadas para el
ejercicio.

> **Uso previsto:** únicamente auditorías de ingeniería social contratadas y autorizadas
> por el cliente, con consentimiento informado y documentado de la persona cuya voz se
> procesa. La voz es un dato biométrico/personal (RGPD): trata el contenido de `storage/`
> como material confidencial del cliente y bórralo al cerrar el caso.

## Cómo funciona

1. Creas un **caso** por auditoría (cliente, persona objetivo, referencia de autorización).
2. Subes uno o varios archivos de audio/vídeo de esa persona. La app:
   - Extrae la pista de audio (si es vídeo) con `ffmpeg`.
   - Normaliza el volumen y recorta silencios largos con `pydub`.
3. Escribes el texto del guion de la llamada y el idioma; la app genera un `.wav` con
   [Coqui XTTS-v2](https://github.com/coqui-ai/TTS), un modelo de clonación de voz
   *zero-shot* multilingüe (no requiere entrenamiento largo: con unos segundos/minutos
   de muestra limpia genera voz nueva en esa voz).
4. El resultado se reproduce y descarga desde la propia interfaz web.

No hay integración con la API de Claude: Claude es un modelo de texto y no genera audio.
Si en el futuro quieres usarlo para redactar o afinar los guiones de la llamada (el texto
que luego se sintetiza), es una pieza independiente que se puede añadir después.

## Requisitos

- Python 3.10+
- `ffmpeg` instalado en el sistema (`apt install ffmpeg`, `brew install ffmpeg`, ...)
- Recomendado: GPU NVIDIA + CUDA para generar audio con rapidez (funciona en CPU, pero
  la síntesis es bastante más lenta)

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

La primera vez que generes un audio, `TTS` descargará automáticamente los pesos del
modelo XTTS-v2 (varios GB) y te pedirá aceptar su licencia
([Coqui Public Model License](https://coqui.ai/cpml/), no comercial salvo licencia de
Coqui) — revísala antes de usar la herramienta en un contexto de servicio facturado a
clientes. Si necesitas un modelo con licencia permisiva para uso comercial, se puede
sustituir en `vclone/voice_engine.py` por alternativas como OpenVoice V2 (MIT).

## Uso

```bash
python app.py
```

Abre `http://127.0.0.1:5000`.

1. Crea un caso con el nombre del cliente, la persona objetivo y la referencia de
   autorización/contrato (campo obligatorio).
2. Sube el material de voz de referencia (mp3, wav, mp4, mov, ...).
3. Escribe el texto del guion y genera el audio.

## Estructura

```
app.py                  # rutas Flask
vclone/config.py        # rutas y parámetros
vclone/db.py            # esquema SQLite (casos, referencias, audios generados)
vclone/audio.py         # extracción de audio y limpieza de silencios
vclone/voice_engine.py  # wrapper de Coqui XTTS-v2
templates/, static/     # interfaz web
storage/, data/         # datos por caso (ignorados por git)
```

## Seguridad y buenas prácticas

- No subas al repositorio nada de `storage/` ni `data/` (ya están en `.gitignore`):
  contienen voces y datos personales de personas reales.
- Guarda junto a cada caso la evidencia de autorización/consentimiento real (contrato,
  correo firmado, etc.) fuera de este repositorio.
- Borra el material de voz al cerrar el caso salvo que el contrato exija conservarlo.
