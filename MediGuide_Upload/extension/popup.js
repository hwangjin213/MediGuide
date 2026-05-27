document.addEventListener('DOMContentLoaded', () => {
  const symptomInput = document.getElementById('symptomInput');
  const submitBtn = document.getElementById('submitBtn');
  const placeholder = document.getElementById('placeholder');
  const loader = document.getElementById('loader');
  const output = document.getElementById('output');
  const symptomTags = document.querySelectorAll('.symptom-tag');
  const langKoBtn = document.getElementById('langKo');
  const langEnBtn = document.getElementById('langEn');

  let currentLang = localStorage.getItem('savedLang') || 'en';

  // --- [추가됨] 대화 초기화 버튼 동적 생성 ---
  const resetBtn = document.createElement('button');
  resetBtn.id = 'resetBtn';
  resetBtn.style.cssText = 'margin-top: 10px; background-color: #374151; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.2s;';
  resetBtn.onmouseover = () => resetBtn.style.backgroundColor = '#4B5563';
  resetBtn.onmouseout = () => resetBtn.style.backgroundColor = '#374151';
  // 분석 버튼 바로 밑에 추가
  submitBtn.parentNode.insertBefore(resetBtn, submitBtn.nextSibling);

  // 초기화 버튼 클릭 시 완벽하게 백지상태로 리셋
  resetBtn.addEventListener('click', () => {
    localStorage.removeItem('savedSymptoms');
    localStorage.removeItem('savedReportHTML');
    symptomInput.value = '';
    output.innerHTML = '';
    output.style.display = 'none';
    placeholder.style.display = 'flex';
  });
  // ------------------------------------------

  const i18n = {
    ko: {
      inputLabel: '환자 발생 증상 입력',
      placeholder: '예: 어제 밤부터 갑작스럽게 38.5도 고열이 나고 누런 가래와 기침이 지속됩니다.',
      submitText: '가이드라인 원클릭 분석',
      resetText: '🔄 대화 내용 초기화',
      resultLabel: '임상 의사 결정 보고서',
      placeholderText: '환자의 증상을 입력하면 데이터베이스의<br>의료 가이드라인을 기반으로 분석을 진행합니다.',
      loadingText: '실시간 AI 분석 및 재시도 중...',
      emptyAlert: '환자의 증상을 구체적으로 입력해 주세요.',
      errorTitle: '🚨 진단 실패',
      errorHint: '클라우드 서버(Render) 연결을 확인하세요.'
    },
    en: {
      inputLabel: 'Enter Patient Symptoms',
      placeholder: 'e.g. Since last night, I\'ve had a high fever of 38.5°C with persistent coughing and yellow phlegm.',
      submitText: 'One-Click Guideline Analysis',
      resetText: '🔄 Reset Conversation',
      resultLabel: 'Clinical Decision Report',
      placeholderText: 'Enter the patient\'s symptoms and the AI will<br>analyze them based on medical guidelines database.',
      loadingText: 'Real-time AI Analyzing & Retrying...',
      emptyAlert: 'Please describe the patient\'s symptoms in detail.',
      errorTitle: '🚨 Diagnosis Failed',
      errorHint: 'Please check the Render cloud server connection.'
    }
  };

  function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('savedLang', lang);
    const t = i18n[lang];

    document.getElementById('inputLabel').textContent = t.inputLabel;
    symptomInput.placeholder = t.placeholder;
    document.getElementById('submitText').textContent = t.submitText;
    resetBtn.textContent = t.resetText; // 리셋 버튼 언어 적용
    document.getElementById('resultLabel').textContent = t.resultLabel;
    document.getElementById('placeholderText').innerHTML = t.placeholderText;
    document.getElementById('loadingText').textContent = t.loadingText;

    symptomTags.forEach(tag => {
      const label = tag.getAttribute('data-label-' + lang);
      if (label) tag.textContent = label;
    });

    if (lang === 'ko') {
      langKoBtn.classList.add('active');
      langEnBtn.classList.remove('active');
    } else {
      langEnBtn.classList.add('active');
      langKoBtn.classList.remove('active');
    }
  }

  applyLanguage(currentLang);

  langKoBtn.addEventListener('click', () => applyLanguage('ko'));
  langEnBtn.addEventListener('click', () => applyLanguage('en'));

  symptomTags.forEach(tag => {
    tag.addEventListener('click', () => {
      const text = tag.getAttribute('data-text-' + currentLang);
      symptomInput.value = text || tag.getAttribute('data-text-ko');
      symptomInput.focus();
      localStorage.setItem('savedSymptoms', symptomInput.value);
    });
  });

  if (localStorage.getItem('savedSymptoms')) {
    symptomInput.value = localStorage.getItem('savedSymptoms');
  }
  if (localStorage.getItem('savedReportHTML')) {
    placeholder.style.display = 'none';
    output.style.display = 'block';
    output.innerHTML = localStorage.getItem('savedReportHTML');
  }

  symptomInput.addEventListener('input', () => {
    localStorage.setItem('savedSymptoms', symptomInput.value);
  });

  submitBtn.addEventListener('click', async () => {
    const symptomText = symptomInput.value.trim();
    const t = i18n[currentLang];

    if (!symptomText) {
      alert(t.emptyAlert);
      return;
    }

    placeholder.style.display = 'none';
    output.style.display = 'none';
    loader.style.display = 'flex';
    submitBtn.disabled = true;
    resetBtn.disabled = true;
    submitBtn.style.opacity = '0.7';
    resetBtn.style.opacity = '0.5';

    try {
      const response = await fetch('https://mediguide-backend-grad.onrender.com/api/diagnose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symptom: symptomText, lang: currentLang })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Server error occurred");
      }

      const data = await response.json();
      const parsedHTML = parseMarkdown(data.ai_analysis);
      
      output.innerHTML = parsedHTML;
      localStorage.setItem('savedReportHTML', parsedHTML);
      
      loader.style.display = 'none';
      output.style.display = 'block';

    } catch (error) {      
      console.error(error);
      loader.style.display = 'none';
      output.style.display = 'block';
      
      let errorMsg = error.message;
      let errorDesc = t.errorHint;
      
      if (errorMsg.includes("429") || errorMsg.includes("RESOURCE_EXHAUSTED") || errorMsg.includes("과부하")) {
          errorMsg = (currentLang === "ko") ? "API 호출 한도를 초과했습니다." : "API Rate Limit Exceeded.";
          errorDesc = (currentLang === "ko") ? "서버가 자동 재시도를 3번 했으나 실패했습니다. 1~2분 뒤 다시 시도해 주세요." : "Auto-retry failed. Please wait 1-2 minutes.";
      } 

      output.innerHTML = 
        '<div style="color: #FF2E93; background: rgba(255, 46, 147, 0.1); border: 1px solid rgba(255, 46, 147, 0.2); padding: 12px; border-radius: 8px;">' +
          '<h4 style="margin-bottom: 6px; font-weight: 700;">' + t.errorTitle + '</h4>' +
          '<p style="font-size: 12px; line-height: 1.5;">' + errorMsg + '</p>' +
          '<p style="font-size: 11px; margin-top: 8px; color: #9CA3AF;">' + errorDesc + '</p>' +
        '</div>';
    } finally {
      submitBtn.disabled = false;
      resetBtn.disabled = false;
      submitBtn.style.opacity = '1';
      resetBtn.style.opacity = '1';
    }
  });

  function parseMarkdown(markdown) {
    let html = markdown;
    html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html = html.replace(/^###[ \t]+(.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##[ \t]+(.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^#[ \t]+(.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 16px 0;">');
    html = html.replace(/^-[ \t]+(.*?)$/gm, '<li>$1</li>');
    html = html.replace(/^\*[ \t]+(.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
    html = html.replace(/^&gt;[ \t]+(.*?)$/gm, '<blockquote style="border-left: 2px solid #00E5FF; padding-left: 10px; color: #9CA3AF; margin: 8px 0;">$1</blockquote>');
    const paragraphs = html.split(/\n{2,}/);
    html = paragraphs.map(p => {
      if (p.trim().startsWith('<h3') || p.trim().startsWith('<ul') || p.trim().startsWith('<blockquote') || p.trim().startsWith('<hr')) {
        return p;
      }
      return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
    }).join('');
    return html;
  }
});