import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from services.analysis_service import AnalysisService
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'ADD_YOUR_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

analysis_service = None


def get_analysis_service():
    global analysis_service
    if analysis_service is None:
        print("Инициализация сервиса анализа...")
        analysis_service = AnalysisService(
            anxiety_model_path="anxiety_model",
            personality_base_model="Vikhrmodels/Vikhr-Qwen-2.5-0.5B-Instruct",
            personality_lora_path="personality_model_vikhr/lora_weights"
        )
        print("Сервис анализа готов!")
    return analysis_service


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'pdf', 'doc', 'docx'}


@app.route('/')
def index():
    if 'user' not in session:
        session['user'] = f'user_{uuid.uuid4().hex[:8]}'
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        service = get_analysis_service()

        # Получаем текст
        text = None
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                os.remove(filepath)
            else:
                return jsonify({'error': 'Неподдерживаемый формат файла'}), 400
        elif 'text' in request.form and request.form['text'].strip():
            text = request.form['text'].strip()
        else:
            return jsonify({'error': 'Необходимо ввести текст или загрузить файл'}), 400

        if len(text.split()) < 10:
            return jsonify({'error': 'Текст слишком короткий. Минимум 10 слов.'}), 400

        analysis_type = request.form.get('analysis_type', 'full')
        model_type = request.form.get('model_type', 'local')
        cloud_model = request.form.get('cloud_model', '')
        user_info = request.form.get('user_info', '')

        if analysis_type == 'anxiety':
            result = service.analyze_anxiety(text, model_type, user_info, cloud_model)
        elif analysis_type == 'big5':
            result = service.analyze_big5(text, model_type, user_info, cloud_model)
        elif analysis_type == 'full':
            result = service.analyze_full(text, 'cloud', user_info, cloud_model)
        else:
            return jsonify({'error': 'Неверный тип анализа'}), 400

        session['last_result'] = result

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Ошибка при анализе: {str(e)}'}), 500


@app.route('/models_info')
def models_info():
    try:
        service = get_analysis_service()
        available_models = service.check_available_models()

        return jsonify({
            'local': {
                'anxiety': 'Локальная модель оценки тревожности',
                'big5': 'Локальная модель Big5',
                'advantages': 'Быстрая работа, не требует интернета',
                'disadvantages': 'Может быть менее точной'
            },
            'cloud': {
                'available_models': available_models,
                'advantages': 'Высокая точность, глубокий анализ',
                'disadvantages': 'Требуется интернет, медленнее'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/check_cloud_models')
def check_cloud_models():
    try:
        service = get_analysis_service()
        available_models = service.check_available_models()

        models_info = []
        for model in available_models:
            info = {'name': model, 'available': True}
            if 'gpt-oss' in model:
                info['description'] = 'Мощная модель для комплексного анализа'
            elif 'qwen' in model:
                info['description'] = 'Быстрая модель для специализированных оценок'
            else:
                info['description'] = 'Доступная облачная модель'
            models_info.append(info)

        return jsonify({
            'available': len(available_models) > 0,
            'models': models_info,
            'count': len(available_models)
        })
    except Exception as e:
        return jsonify({
            'available': True,
            'models': [
                {'name': 'gpt-oss:120b-cloud', 'available': True,
                 'description': 'Мощная модель для комплексного анализа'},
                {'name': 'qwen3-next:80b-cloud', 'available': True,
                 'description': 'Быстрая модель для специализированных оценок'}
            ],
            'count': 2
        })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    try:
        service = get_analysis_service()
        print("Сервис инициализирован успешно")
    except Exception as e:
        print(f"Предупреждение: {e}")

    app.run(host='0.0.0.0', port=5000, debug=True)