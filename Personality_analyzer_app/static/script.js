// Ждем загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('Приложение загружено');

    // Основные элементы
    const form = document.getElementById('analysisForm');
    const analysisCard = document.getElementById('analysisCard');
    const results = document.getElementById('results');
    const resultsContent = document.getElementById('resultsContent');
    const loading = document.getElementById('loadingIndicator');
    const textarea = document.getElementById('text');
    const fileInput = document.getElementById('file');
    const fileName = document.getElementById('fileName');
    const wordCount = document.getElementById('wordCount');
    const modelTypeGroup = document.getElementById('modelTypeGroup');
    const cloudModelGroup = document.getElementById('cloudModelGroup');
    const cloudModelSelect = document.getElementById('cloud_model');
    const refreshModelsBtn = document.getElementById('refreshModels');
    const modelStatus = document.getElementById('modelStatus');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const newAnalysisBtn = document.getElementById('newAnalysis');

    // Проверяем, что все элементы найдены
    if (!form) {
        console.error('Форма не найдена!');
        return;
    }

    // Инициализация
    updateWordCount();
    checkCloudModels();

    // Обработчики событий
    textarea.addEventListener('input', updateWordCount);

    fileInput.addEventListener('change', function(e) {
        if (this.files && this.files.length > 0) {
            fileName.textContent = this.files[0].name;
        } else {
            fileName.textContent = '';
        }
    });

    // Обработка переключения типа анализа
    const analysisTypeRadios = document.querySelectorAll('input[name="analysis_type"]');
    analysisTypeRadios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            if (this.value === 'full') {
                // Для полного анализа только облачная модель
                const cloudRadio = document.querySelector('input[name="model_type"][value="cloud"]');
                if (cloudRadio) {
                    cloudRadio.checked = true;
                }
                modelTypeGroup.style.opacity = '0.5';
                modelTypeGroup.querySelectorAll('input').forEach(function(input) {
                    input.disabled = true;
                });
                showCloudModelSelect();
            } else {
                modelTypeGroup.style.opacity = '1';
                modelTypeGroup.querySelectorAll('input').forEach(function(input) {
                    input.disabled = false;
                });
                updateCloudModelVisibility();
            }
        });
    });

    // Обработка переключения типа модели
    const modelTypeRadios = document.querySelectorAll('input[name="model_type"]');
    modelTypeRadios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            updateCloudModelVisibility();
        });
    });

    function updateCloudModelVisibility() {
        const modelType = document.querySelector('input[name="model_type"]:checked');
        if (modelType && modelType.value === 'cloud') {
            showCloudModelSelect();
        } else {
            hideCloudModelSelect();
        }
    }

    function showCloudModelSelect() {
        if (cloudModelGroup) {
            cloudModelGroup.style.display = 'block';
        }
    }

    function hideCloudModelSelect() {
        if (cloudModelGroup) {
            cloudModelGroup.style.display = 'none';
        }
    }

    // Обновление счетчика слов
    function updateWordCount() {
        if (!textarea || !wordCount) return;

        const text = textarea.value.trim();
        const words = text ? text.split(/\s+/).filter(function(word) {
            return word.length > 0;
        }) : [];

        wordCount.textContent = words.length;

        if (words.length < 10) {
            wordCount.style.color = '#f44336';
        } else {
            wordCount.style.color = '#4caf50';
        }
    }

    // Проверка облачных моделей
    async function checkCloudModels() {
        try {
            if (modelStatus) {
                modelStatus.textContent = 'Проверка доступных моделей...';
            }

            const response = await fetch('/check_cloud_models');
            const data = await response.json();

            if (data.available && data.models && data.models.length > 0) {
                updateCloudModelSelect(data.models);
                if (modelStatus) {
                    modelStatus.textContent = '✅ Доступно моделей: ' + data.models.length;
                    modelStatus.style.color = '#4caf50';
                }
            } else {
                if (cloudModelSelect) {
                    cloudModelSelect.innerHTML = '<option value="">Нет доступных моделей</option>';
                }
                if (modelStatus) {
                    modelStatus.textContent = '❌ Облачные модели недоступны';
                    modelStatus.style.color = '#f44336';
                }
            }
        } catch (error) {
            console.error('Ошибка проверки моделей:', error);
            if (modelStatus) {
                modelStatus.textContent = '⚠️ Ошибка проверки моделей';
                modelStatus.style.color = '#ff9800';
            }
        }
    }

    function updateCloudModelSelect(models) {
        if (!cloudModelSelect) return;

        cloudModelSelect.innerHTML = '<option value="">Автоматический выбор</option>';

        models.forEach(function(model) {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name;
            cloudModelSelect.appendChild(option);
        });
    }

    // Обновление списка моделей
    if (refreshModelsBtn) {
        refreshModelsBtn.addEventListener('click', async function() {
            this.disabled = true;
            this.textContent = '⏳ Обновление...';
            await checkCloudModels();
            this.disabled = false;
            this.textContent = '🔄 Обновить список моделей';
        });
    }

    // Отправка формы
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Форма отправлена');

            // Проверка текста
            const text = textarea ? textarea.value.trim() : '';
            const file = fileInput ? fileInput.files[0] : null;

            if (!text && !file) {
                alert('Пожалуйста, введите текст или загрузите файл');
                return;
            }

            // Проверка количества слов
            const words = text ? text.split(/\s+/).filter(function(word) {
                return word.length > 0;
            }) : [];

            if (words.length < 10 && !file) {
                alert('Текст должен содержать минимум 10 слов');
                return;
            }

            // Показываем загрузку
            if (analysisCard) analysisCard.style.display = 'none';
            if (results) results.style.display = 'block';
            if (loading) loading.style.display = 'block';
            if (resultsContent) resultsContent.innerHTML = '';
            if (analyzeBtn) analyzeBtn.disabled = true;

            // Собираем данные
            const formData = new FormData(form);

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (loading) loading.style.display = 'none';

                if (data.success) {
                    displayResults(data.result);
                } else {
                    displayError(data.error || 'Неизвестная ошибка');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                if (loading) loading.style.display = 'none';
                displayError('Ошибка соединения с сервером: ' + error.message);
            } finally {
                if (analyzeBtn) analyzeBtn.disabled = false;
            }
        });
    }

    // Отображение результатов
    function displayResults(result) {
        if (!resultsContent) return;

        let html = '<div class="model-badge">';
        html += 'Модель: <strong>' + (result.model_name || 'Неизвестно') + '</strong>';
        html += ' (' + (result.model_type === 'cloud' ? '☁️ облачная' : '💻 локальная') + ')';
        html += '</div>';

        if (result.type === 'anxiety') {
            html += renderAnxietyResults(result.result);
        } else if (result.type === 'big5') {
            html += renderBig5Results(result.result);
        } else if (result.type === 'full') {
            html += renderFullResults(result.result);
        }

        resultsContent.innerHTML = html;
        results.scrollIntoView({ behavior: 'smooth' });
    }

    function renderAnxietyResults(result) {
        console.log('Данные для отображения:', result);

        const diagnosis = result.diagnosis || 'НЕТ ТРЕВОЖНОСТИ';
        const isAnxiety = diagnosis === 'ТРЕВОЖНОСТЬ';
        const rationale = result.rationale || result.analysis || '';
        const rawOutput = result.raw_output || '';

        let html = '';

        // Основной результат
        html += '<div class="diagnosis-card">';
        html += '<h3>🔍 Результат анализа тревожности</h3>';

        // Диагноз
        html += '<div class="diagnosis-result ' + (isAnxiety ? 'anxiety-positive' : 'anxiety-negative') + '">';
        html += '<div class="diagnosis-icon">' + (isAnxiety ? '⚠️' : '✅') + '</div>';
        html += '<div class="diagnosis-text">';
        html += '<h2>Диагноз: ' + diagnosis + '</h2>';
        html += '</div>';
        html += '</div>';

        // Обоснование
        if (rationale && rationale !== 'Текст слишком короткий для анализа') {
            html += '<div class="rationale-box">';
            html += '<h4>📝 Обоснование</h4>';
            html += '<p>' + rationale + '</p>';
            html += '</div>';
        } else {
            html += '<div class="rationale-box" style="border-left-color: #ff9800;">';
            html += '<h4>⚠️ Обоснование отсутствует</h4>';
            html += '<p>Модель не смогла сформулировать обоснование. Проверьте полный ответ модели.</p>';
            html += '</div>';
        }

        html += '</div>'; // конец diagnosis-card

        // Полный ответ модели (для отладки)
        if (rawOutput) {
            html += '<div class="info-section">';
            html += '<details>';
            html += '<summary style="cursor: pointer; color: #667eea;">🔍 Показать полный ответ модели</summary>';
            html += '<pre class="raw-output">' + escapeHtml(rawOutput) + '</pre>';
            html += '</details>';
            html += '</div>';
        }

        return html;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderBig5Results(result) {
        console.log('Отображение результатов Big5:', result);

        if (result.error) {
            return '<div class="error-message"><p>❌ ' + result.error + '</p></div>';
        }

        // Определяем тип данных: локальная модель (0-2) или облачная (0-100)
        const traits = result.traits || result.analysis || {};
        const traitEntries = Object.entries(traits).filter(([key, value]) => typeof value === 'object');

        if (traitEntries.length === 0) {
            // Проверяем predictions (формат локальной модели)
            if (result.predictions) {
                return renderLocalBig5Results(result);
            }
            return '<div class="error-message"><p>Нет данных для отображения</p></div>';
        }

        // Определяем, локальная модель или облачная
        const firstScore = traitEntries[0]?.[1]?.score;
        const isLocalModel = firstScore !== undefined && firstScore <= 2;

        if (isLocalModel || result.predictions) {
            return renderLocalBig5Results(result);
        } else {
            return renderCloudBig5Results(result);
        }
    }

    function renderLocalBig5Results(result) {
        // Локальная модель возвращает оценки 0, 1, 2
        const predictions = result.predictions || result.traits || result.analysis || {};

        const traitNames = {
            "открытость_опыту": "Открытость опыту",
            "добросовестность": "Добросовестность",
            "экстраверсия": "Экстраверсия",
            "доброжелательность": "Доброжелательность",
            "нейротизм": "Нейротизм"
        };

        const traitDescriptions = {
            "открытость_опыту": "Любознательность, креативность, воображение",
            "добросовестность": "Организованность, дисциплина, надёжность",
            "экстраверсия": "Общительность, энергичность, социальная активность",
            "доброжелательность": "Эмпатия, сотрудничество, доверие к людям",
            "нейротизм": "Эмоциональная нестабильность, тревожность"
        };

        const levelNames = {
            0: "Низкий",
            1: "Средний",
            2: "Высокий"
        };

        const levelColors = {
            0: "#4caf50",
            1: "#ff9800",
            2: "#2196f3"
        };

        const levelIcons = {
            0: "📉",
            1: "📊",
            2: "📈"
        };

        let html = '<h3>🎭 Профиль личности Big5 (Локальная модель)</h3>';
        html += '<p class="model-note">Оценки: 0 - низкий уровень, 1 - средний уровень, 2 - высокий уровень</p>';
        html += '<div class="traits-grid">';

        for (const [trait, data] of Object.entries(predictions)) {
            if (trait === 'raw_output' || trait === 'error') continue;

            let score, level, description;

            if (typeof data === 'object' && data !== null) {
                score = data.score !== undefined ? data.score : data;
                level = data.level || levelNames[score] || 'Не определен';
                description = data.description || traitDescriptions[trait] || '';
            } else {
                score = data;
                level = levelNames[score] || 'Не определен';
                description = traitDescriptions[trait] || '';
            }

            const traitName = traitNames[trait] || trait.replace(/_/g, ' ');
            const color = levelColors[score] || "#667eea";
            const icon = levelIcons[score] || "📊";

            // Шкала для локальной модели (0-2)
            const barWidth = (score / 2) * 100;
            const barSegments = [0, 1, 2];

            html += `
                <div class="trait-card local-model">
                    <div class="trait-header">
                        <span class="trait-icon">${icon}</span>
                        <div class="trait-info">
                            <span class="trait-name">${traitName}</span>
                            <span class="trait-score" style="color: ${color}">${score}/2</span>
                        </div>
                    </div>

                    <div class="trait-bar-container">
                        <div class="trait-bar local-scale">
                            <div class="trait-bar-fill" style="width: ${barWidth}%; background: ${color}"></div>
                        </div>
                        <div class="trait-scale-labels">
                            <span class="${score === 0 ? 'active' : ''}" style="color: ${score === 0 ? color : '#999'}">0 - Низкий</span>
                            <span class="${score === 1 ? 'active' : ''}" style="color: ${score === 1 ? color : '#999'}">1 - Средний</span>
                            <span class="${score === 2 ? 'active' : ''}" style="color: ${score === 2 ? color : '#999'}">2 - Высокий</span>
                        </div>
                    </div>

                    <div class="trait-details">
                        <div class="trait-level" style="color: ${color}">
                            <strong>Уровень: ${level}</strong>
                        </div>
                        <div class="trait-description">${description}</div>
                    </div>
                </div>
            `;
        }

        html += '</div>';

        // Сырой ответ модели (для отладки)
        if (result.raw_output) {
            html += '<div class="info-section" style="margin-top: 20px;">';
            html += '<details>';
            html += '<summary style="cursor: pointer; color: #667eea;">🔍 Показать полный ответ модели</summary>';
            html += '<pre class="raw-output">' + escapeHtml(result.raw_output) + '</pre>';
            html += '</details>';
            html += '</div>';
        }

        return html;
    }

    function renderCloudBig5Results(result) {
        // Облачная модель возвращает оценки 0-100
        const traits = result.traits || result.analysis || {};

        const traitNames = {
            "открытость_опыту": "Открытость опыту",
            "добросовестность": "Добросовестность",
            "экстраверсия": "Экстраверсия",
            "доброжелательность": "Доброжелательность",
            "нейротизм": "Нейротизм"
        };

        let html = '<h3>🎭 Профиль личности Big5 (Облачная модель)</h3>';
        html += '<p class="model-note">Оценки: 0-100%</p>';
        html += '<div class="traits-grid">';

        for (const [trait, data] of Object.entries(traits)) {
            if (typeof data !== 'object' || data === null) continue;

            const score = data.score || 0;
            const level = data.level || getLevelText(score);
            const description = data.description || '';
            const traitName = traitNames[trait] || trait.replace(/_/g, ' ');
            const color = getCloudTraitColor(score);

            html += `
                <div class="trait-card cloud-model">
                    <div class="trait-header">
                        <span class="trait-name">${traitName}</span>
                        <span class="trait-score" style="color: ${color}">${score}%</span>
                    </div>
                    <div class="trait-bar">
                        <div class="trait-bar-fill" style="width: ${score}%; background: ${color}"></div>
                    </div>
                    <div class="trait-details">
                        <div class="trait-level" style="color: ${color}">${level}</div>
                        ${description ? `<div class="trait-description">${description}</div>` : ''}
                    </div>
                </div>
            `;
        }

        html += '</div>';

        if (result.summary || result.personality_summary) {
            html += `
                <div class="info-section">
                    <h4>📝 Общее описание</h4>
                    <p>${result.summary || result.personality_summary}</p>
                </div>
            `;
        }

        return html;
    }

    function getLevelText(score) {
        if (score <= 33) return 'Низкий';
        if (score <= 66) return 'Средний';
        return 'Высокий';
    }

    function getCloudTraitColor(score) {
        if (score <= 33) return '#4caf50';
        if (score <= 66) return '#ff9800';
        return '#2196f3';
    }

    // Обновленная функция отображения результатов
    function displayResults(result) {
        if (!resultsContent) return;

        let html = '';

        // Бейдж с информацией о модели
        html += '<div class="model-badge">';
        html += '🧠 Модель: <strong>' + (result.model_name || 'Неизвестно') + '</strong>';
        html += ' (' + (result.model_type === 'cloud' ? '☁️ облачная' : '💻 локальная') + ')';
        if (result.analysis_timestamp) {
            html += '<br><small>🕐 ' + new Date(result.analysis_timestamp).toLocaleString('ru-RU') + '</small>';
        }
        html += '</div>';

        if (result.type === 'anxiety') {
            html += renderAnxietyResults(result.result);
        } else if (result.type === 'big5') {
            html += renderBig5Results(result.result);
        } else if (result.type === 'full') {
            html += renderFullResults(result.result);
        }

        resultsContent.innerHTML = html;

        // Анимация появления
        setTimeout(() => {
            document.querySelectorAll('.trait-bar-fill').forEach(bar => {
                bar.style.transition = 'width 1s ease';
            });
        }, 100);

        results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderFullResults(result) {
        if (!result) return '<p>Нет данных</p>';

        let html = '<h2>📊 Полный анализ личности</h2>';

        if (result.anxiety) {
            html += '<h3>😰 Тревожность</h3>';
            html += '<p>Уровень: <strong>' + result.anxiety.level + '/10</strong></p>';
            if (result.anxiety.description) {
                html += '<p>' + result.anxiety.description + '</p>';
            }
        }

        if (result.big5) {
            html += '<h3>🎭 Big5</h3>';
            html += renderBig5Results({traits: result.big5});
        }

        if (result.personality_type) {
            html += '<p><strong>Тип личности:</strong> ' + result.personality_type + '</p>';
        }

        if (result.summary) {
            html += '<h3>📝 Резюме</h3>';
            html += '<p>' + result.summary + '</p>';
        }

        if (result.recommendations && result.recommendations.length > 0) {
            html += '<h4>💡 Рекомендации:</h4><ul>';
            result.recommendations.forEach(function(r) {
                html += '<li>' + r + '</li>';
            });
            html += '</ul>';
        }

        return html;
    }

    function displayError(message) {
        if (!resultsContent) return;

        resultsContent.innerHTML = '<div class="error-message">' +
            '<h4>❌ Ошибка</h4>' +
            '<p>' + message + '</p>' +
            '</div>';
    }

    // Кнопка нового анализа
    if (newAnalysisBtn) {
        newAnalysisBtn.addEventListener('click', function() {
            if (results) results.style.display = 'none';
            if (analysisCard) analysisCard.style.display = 'block';
            if (resultsContent) resultsContent.innerHTML = '';
            if (textarea) textarea.value = '';
            updateWordCount();
            window.scrollTo(0, 0);
        });
    }

    // Начальная настройка
    updateCloudModelVisibility();
});