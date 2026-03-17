#!/usr/bin/env python3
# ============================================================
#  ConnectPro — Servidor de Codigos
#  Mapeia codigo numerico (ex: 482731) -> URL do Cloudflare
#  Deploy no Render.com (gratuito)
# ============================================================

from flask import Flask, request, jsonify
import random, time, threading

app = Flask(__name__)

# Armazena: { "482731": { "url": "wss://...", "expires": timestamp } }
_sessions = {}
_lock     = threading.Lock()
SESSION_TTL = 3600  # 1 hora


def _cleanup():
    """Remove sessoes expiradas periodicamente."""
    while True:
        time.sleep(60)
        now = time.time()
        with _lock:
            expired = [k for k, v in _sessions.items() if v['expires'] < now]
            for k in expired:
                del _sessions[k]

threading.Thread(target=_cleanup, daemon=True).start()


def _gen_code() -> str:
    """Gera codigo numerico unico de 6 digitos."""
    with _lock:
        for _ in range(100):
            code = str(random.randint(100000, 999999))
            if code not in _sessions:
                return code
    return str(random.randint(100000, 999999))


@app.route('/register', methods=['POST'])
def register():
    """Agent registra a URL do tunel e recebe o codigo numerico."""
    data = request.get_json(force=True)
    url  = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'url obrigatoria'}), 400

    code = _gen_code()
    with _lock:
        _sessions[code] = {
            'url':     url,
            'expires': time.time() + SESSION_TTL
        }
    return jsonify({'code': code})


@app.route('/resolve/<code>', methods=['GET'])
def resolve(code):
    """Viewer consulta o codigo e recebe a URL do tunel."""
    code = code.strip()
    with _lock:
        session = _sessions.get(code)
    if not session:
        return jsonify({'error': 'codigo invalido ou expirado'}), 404
    if session['expires'] < time.time():
        with _lock:
            _sessions.pop(code, None)
        return jsonify({'error': 'codigo expirado'}), 404
    return jsonify({'url': session['url']})


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
