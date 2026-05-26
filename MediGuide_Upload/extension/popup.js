document.addEventListener("DOMContentLoaded", () => {
  const symptomInput = document.getElementById("symptomInput");
  const submitBtn = document.getElementById("submitBtn");
  const placeholder = document.getElementById("placeholder");
  const loader = document.getElementById("loader");
  const output = document.getElementById("output");
  const symptomTags = document.querySelectorAll(".symptom-tag");
  const langKoBtn = document.getElementById("langKo");
  const langEnBtn = document.getElementById("langEn");

  // i18n state
  let currentLang = "ko";

  // i18n translation table
  const i18n = {
    ko: {
      inputLabel: "환자 발생 증상 입력",
      placeholder: "예: 어제 밤부터 갑작스럽게 38.5도 고열이 나고 누런 가래와 기침이 지속돼요.",
      submitText: "가이드라인 원클릭 분석",
      resultLabel: "임상 의사 결정 보고서",
      placeholderText: "환자의 증상을 입력하면 데이터베이스의<br>의료 가이드라인을 기반으로 분석이 진행됩니다.",
      loadingText: "Gemini & MongoDB MCP 분석 중...",
      emptyAlert: "환자의 증상을 구체적으로 입력해 주세요.",
      errorTitle: "🚨 진단 실패",
      errorHint: "FastAPI 백엔드(localhost:8000)가 정상 실행 중인지 확인하세요."
    },
    en: {
      inputLabel: "Enter Patient Symptoms",
      placeholder: "e.g. Since last night, I've had a high fever of 38.5°C with persistent coughing and yellow phlegm.",
      submitText: "One-Click Guideline Analysis",
      resultLabel: "Clinical Decision Report",
      placeholderText: "Enter the patient's symptoms and the AI will<br>analyze them based on medical guidelines database.",
      loadingText: "Analyzing via Gemini & MongoDB MCP...",
      emptyAlert: "Please describe the patient's symptoms in detail.",
      errorTitle: "🚨 Diagnosis Failed",
      errorHint: "Please ensure the FastAPI backend (localhost:8000) is running."
    }
  };

  // Update all UI texts when language changes
  function applyLanguage(lang) {
    currentLang = lang;
    const t = i18n[lang];

    document.getElementById("inputLabel").textContent = t.inputLabel;
    symptomInput.placeholder = t.placeholder;
    document.getElementById("submitText").textContent = t.submitText;
    document.getElementById("resultLabel").textContent = t.resultLabel;
    document.getElementById("placeholderText").innerHTML = t.placeholderText;
    document.getElementById("loadingText").textContent = t.loadingText;

    // Update quick tag labels
    symptomTags.forEach(tag => {
      const label = tag.getAttribute(`data-label-${lang}`);
      if (label) tag.textContent = label;
    });

    // Toggle active button style
    if (lang === "ko") {
      langKoBtn.classList.add("active");
      langEnBtn.classList.remove("active");
    } else {
      langEnBtn.classList.add("active");
      langKoBtn.classList.remove("active");
    }
  }

  // Language toggle event listeners
  langKoBtn.addEventListener("click", () => applyLanguage("ko"));
  langEnBtn.addEventListener("click", () => applyLanguage("en"));

  // Quick tag click fills textarea
  symptomTags.forEach(tag => {
    tag.addEventListener("click", () => {
      const text = tag.getAttribute(`data-text-${currentLang}`);
      symptomInput.value = text || tag.getAttribute("data-text-ko");
      symptomInput.focus();
    });
  });

  // Submit diagnosis request
  submitBtn.addEventListener("click", async () => {
    const symptomText = symptomInput.value.trim();
    const t = i18n[currentLang];

    if (!symptomText) {
      alert(t.emptyAlert);
      return;
    }

    // Toggle loading UI
    placeholder.style.display = "none";
    output.style.display = "none";
    loader.style.display = "flex";
    submitBtn.disabled = true;
    submitBtn.style.opacity = "0.7";

    try {
      const response = await fetch("http://localhost:8000/api/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptom: symptomText, lang: currentLang })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Server response error.");
      }

      const data = await response.json();
      output.innerHTML = parseMarkdown(data.ai_analysis);
      loader.style.display = "none";
      output.style.display = "block";

    } catch (error) {
      console.error(error);
      loader.style.display = "none";
      output.style.display = "block";
      output.innerHTML = `
        <div style="color: #FF2E93; background: rgba(255, 46, 147, 0.1); border: 1px solid rgba(255, 46, 147, 0.2); padding: 12px; border-radius: 8px;">
          <h4 style="margin-bottom: 6px; font-weight: 700;">${t.errorTitle}</h4>
          <p style="font-size: 12px; line-height: 1.5;">${error.message}</p>
          <p style="font-size: 11px; margin-top: 8px; color: #9CA3AF;">${t.errorHint}</p>
        </div>
      `;
    } finally {
      submitBtn.disabled = false;
      submitBtn.style.opacity = "1";
    }
  });

  /**
   * Safe Markdown to HTML parser
   */
  function parseMarkdown(markdown) {
    let html = markdown;

    // Sanitize
    html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    // Headers
    html = html.replace(/^###[ \t]+(.*?)$/gm, "<h3>$1</h3>");
    html = html.replace(/^##[ \t]+(.*?)$/gm, "<h3>$1</h3>");
    html = html.replace(/^#[ \t]+(.*?)$/gm, "<h3>$1</h3>");

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // HR
    html = html.replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 16px 0;">');

    // Bullets
    html = html.replace(/^-[ \t]+(.*?)$/gm, "<li>$1</li>");
    html = html.replace(/^\*[ \t]+(.*?)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*?<\/li>)+/gs, "<ul>$&</ul>");

    // Blockquotes
    html = html.replace(/^&gt;[ \t]+(.*?)$/gm, '<blockquote style="border-left: 2px solid #00E5FF; padding-left: 10px; color: #9CA3AF; margin: 8px 0;">$1</blockquote>');

    // Paragraphs
    const paragraphs = html.split(/\n{2,}/);
    html = paragraphs.map(p => {
      if (p.trim().startsWith("<h3") || p.trim().startsWith("<ul") || p.trim().startsWith("<blockquote") || p.trim().startsWith("<hr")) {
        return p;
      }
      return `<p>${p.replace(/\n/g, "<br>")}</p>`;
    }).join("");

    return html;
  }
});
