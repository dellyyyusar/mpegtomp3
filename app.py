import os
import subprocess
import uuid
from flask import Flask, render_template, request, send_file, jsonify, url_for

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

FFMPEG_PATH = r"C:\Users\gh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"

def get_ffmpeg():
    for p in [FFMPEG_PATH, "ffmpeg"]:
        try:
            subprocess.run([p, "-version"], capture_output=True, check=True)
            return p
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None

@app.route('/')
def index():
    return render_template('index.html', ffmpeg_installed=get_ffmpeg() is not None)

@app.route('/convert', methods=['POST'])
def convert():
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        return jsonify({'error': 'ffmpeg tidak ditemukan'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang diupload'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nama file kosong'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    allowed = {'mpg', 'mpeg', 'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'ts', 'mts', 'm2ts', 'vob'}
    if ext not in allowed:
        return jsonify({'error': f'Format .{ext} tidak didukung. Gunakan: {", ".join(sorted(allowed))}'}), 400

    file_id = uuid.uuid4().hex
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}.{ext}')
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{file_id}.mp3')
    file.save(input_path)

    bitrate = request.form.get('bitrate', '192')
    cmd = [ffmpeg, '-i', input_path, '-vn', '-codec:a', 'libmp3lame', '-b:a', f'{bitrate}k', '-y', output_path]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        original_name = file.filename.rsplit('.', 1)[0] + '.mp3'
        return jsonify({
            'download_url': url_for('download', filename=f'{file_id}.mp3', name=original_name),
            'filename': original_name,
            'size': os.path.getsize(output_path)
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Konversi timeout (5 menit)'}), 504
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode('utf-8', errors='replace')[-500:]
        return jsonify({'error': f'Konversi gagal: {err}'}), 500

@app.route('/download/<filename>')
def download(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(path):
        return jsonify({'error': 'File tidak ditemukan'}), 404
    name = request.args.get('name') or filename
    return send_file(path, as_attachment=True, download_name=name)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'ffmpeg': get_ffmpeg() is not None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
