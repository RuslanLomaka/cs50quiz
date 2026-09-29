let QUIZ = null;

const I18N = window.QUIZFORGER_I18N || {};
function t(key, fallback) {
  return I18N[key] || fallback;
}

function getCookie(name) {
  const cookieValue = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));
  if (!cookieValue) return null;
  return decodeURIComponent(cookieValue.split("=").slice(1).join("="));
}

function newSubmissionId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function shuffleArray(items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const target = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[target]] = [copy[target], copy[index]];
  }
  return copy;
}

function answerLetter(index) {
  return String.fromCharCode(65 + index);
}

function normalizeSourceUrl(rawUrl) {
  if (typeof rawUrl !== "string") return "";
  const trimmed = rawUrl.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return "";
}

document.addEventListener("DOMContentLoaded", async () => {
  const titleEl = document.querySelector("#title");
  const quizEl = document.querySelector("#quiz");
  const resultEl = document.querySelector("#result");
  const checkBtn = document.querySelector("#check");
  const attemptStatusEl = document.querySelector("#attemptStatus");
  const submissionId = newSubmissionId();

  const setError = (message) => {
    if (titleEl) titleEl.textContent = t("error", "Error");
    if (quizEl) quizEl.textContent = message;
    if (resultEl) resultEl.textContent = "";
  };

  const setAttemptStatus = (message, isError = false) => {
    if (!attemptStatusEl) return;
    attemptStatusEl.textContent = message;
    attemptStatusEl.classList.toggle("text-danger", isError);
    attemptStatusEl.classList.toggle("text-muted", !isError);
  };

  const saveAttempt = async (quizId, answers) => {
    const response = await fetch(`/api/quizzes/${encodeURIComponent(quizId)}/attempts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken") || "",
      },
      body: JSON.stringify({ submission_id: submissionId, answers }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || t("failedToSaveAttempt", "Failed to save attempt"));
    }
    return payload;
  };

  const renderSources = (body, sources) => {
    const safeSources = (Array.isArray(sources) ? sources : [])
      .map((source) => ({ ...source, normalizedUrl: normalizeSourceUrl(source?.url) }))
      .filter((source) => source.normalizedUrl);
    if (safeSources.length === 0) return;

    const wrap = document.createElement("div");
    wrap.className = "question-sources border-top mt-3 pt-3";
    const heading = document.createElement("div");
    heading.className = "fw-semibold small text-uppercase text-muted mb-2";
    heading.textContent = t("sources", "Sources");
    wrap.appendChild(heading);

    const list = document.createElement("div");
    list.className = "vstack gap-2";
    safeSources.forEach((source, sourceIndex) => {
      const item = document.createElement("div");
      const link = document.createElement("a");
      link.href = source.normalizedUrl;
      link.target = "_blank";
      link.rel = "noreferrer noopener";
      link.textContent = source.title?.trim() || `${t("source", "Source")} ${sourceIndex + 1}`;
      item.appendChild(link);
      if (source.note) {
        const note = document.createElement("div");
        note.className = "small text-muted";
        note.textContent = source.note;
        item.appendChild(note);
      }
      list.appendChild(item);
    });
    wrap.appendChild(list);
    body.appendChild(wrap);
  };

  const renderFeedback = (feedback) => {
    feedback.forEach((item) => {
      const card = document.querySelector(`.card[data-question-index="${item.question_index}"]`);
      const body = card?.querySelector(".card-body");
      if (!card || !body) return;

      const correctIndexes = new Set(item.correct_answer_indices || []);
      const labels = Array.from(card.querySelectorAll(".form-check-label"));
      const selectedInputs = Array.from(card.querySelectorAll("input:checked"));
      labels.forEach((label) => {
        const answerIndex = Number(label.dataset.answerIndex);
        if (correctIndexes.has(answerIndex)) label.classList.add("fw-bold", "revealed-correct");
      });
      selectedInputs.forEach((input) => {
        const label = card.querySelector(`label[for="${CSS.escape(input.id)}"]`);
        if (!label) return;
        const answerIndex = Number(input.dataset.answerIndex);
        label.classList.add(correctIndexes.has(answerIndex) ? "text-success" : "text-danger");
      });

      card.classList.add(item.status === "correct" ? "border-success" : "border-danger");
      const correctText = labels
        .filter((label) => correctIndexes.has(Number(label.dataset.answerIndex)))
        .map((label) => label.textContent?.trim() || "")
        .filter(Boolean)
        .join("; ");
      let lead;
      if (item.status === "correct") {
        lead = t("gotRight", "You got this right.");
      } else if (item.status === "missed") {
        lead = `${t("missedQuestion", "You missed this question.")} ${correctIndexes.size > 1 ? t("answersWere", "The correct answers were") : t("answerWas", "The correct answer was")}: ${correctText}.`;
      } else {
        lead = `${t("wrongAnswer", "Your answer was not correct.")} ${correctIndexes.size > 1 ? t("answersWere", "The correct answers were") : t("answerWas", "The correct answer was")}: ${correctText}.`;
      }

      const wrap = document.createElement("div");
      wrap.className = "question-feedback mt-3 pt-3";
      const leadEl = document.createElement("div");
      leadEl.className = `fw-semibold ${item.status === "correct" ? "text-success" : item.status === "missed" ? "text-muted" : "text-danger"}`;
      leadEl.textContent = lead;
      wrap.appendChild(leadEl);

      if (item.explanation) {
        const explanationWrap = document.createElement("div");
        explanationWrap.className = "question-explanation mt-3";
        const explanationTitle = document.createElement("div");
        explanationTitle.className = "small fw-semibold text-uppercase text-muted mb-1";
        explanationTitle.textContent = t("explanation", "Explanation");
        const explanationEl = document.createElement("div");
        explanationEl.className = "small";
        explanationEl.textContent = item.explanation;
        explanationWrap.append(explanationTitle, explanationEl);
        wrap.appendChild(explanationWrap);
      }
      body.appendChild(wrap);
      renderSources(body, item.sources);
    });
  };

  try {
    const quizId = window.QUIZ_ID;
    if (!quizId) throw new Error(t("missingQuizId", "QUIZ_ID is missing"));
    const response = await fetch(`/api/quizzes/${encodeURIComponent(quizId)}`);
    if (!response.ok) throw new Error(t("failedToLoadQuiz", "Failed to load quiz"));
    QUIZ = await response.json();
    if (titleEl) titleEl.textContent = QUIZ.title ?? t("quiz", "Quiz");
    if (!quizEl) return;
    quizEl.innerHTML = "";

    (QUIZ.questions ?? []).forEach((question, questionIndex) => {
      const card = document.createElement("div");
      card.className = "card shadow-sm";
      card.dataset.questionIndex = questionIndex;
      const body = document.createElement("div");
      body.className = "card-body";
      const questionText = document.createElement("div");
      questionText.className = "card-title fw-semibold";
      questionText.textContent = `${questionIndex + 1}. ${question.question ?? ""}`;
      body.appendChild(questionText);

      if (question.multiple) {
        const note = document.createElement("div");
        note.className = "small text-muted mt-2";
        note.textContent = t("multiNote", "This question has more than 1 correct answer.");
        body.appendChild(note);
      }

      const answersWrap = document.createElement("div");
      answersWrap.className = "vstack gap-2 mt-3";
      shuffleArray(question.answers ?? []).forEach((answer, displayIndex) => {
        const inputId = `q${questionIndex}_a${displayIndex}`;
        const wrap = document.createElement("div");
        wrap.className = "form-check";
        const input = document.createElement("input");
        input.className = "form-check-input";
        input.type = question.multiple ? "checkbox" : "radio";
        input.name = `q_${questionIndex}`;
        input.id = inputId;
        input.dataset.answerIndex = answer.index;
        const label = document.createElement("label");
        label.className = "form-check-label";
        label.htmlFor = inputId;
        label.dataset.answerIndex = answer.index;
        label.textContent = `${answerLetter(displayIndex)}. ${answer.text ?? ""}`;
        wrap.append(input, label);
        answersWrap.appendChild(wrap);
      });
      body.appendChild(answersWrap);
      card.appendChild(body);
      quizEl.appendChild(card);
    });

    checkBtn?.addEventListener("click", async () => {
      if (!QUIZ || checkBtn.disabled) return;
      checkBtn.disabled = true;
      setAttemptStatus("");
      const answers = (QUIZ.questions ?? []).map((_, questionIndex) => {
        const card = document.querySelector(`.card[data-question-index="${questionIndex}"]`);
        const answerIndices = Array.from(card?.querySelectorAll("input:checked") || []).map((input) =>
          Number(input.dataset.answerIndex),
        );
        return { question_index: questionIndex, answer_indices: answerIndices };
      });

      try {
        const result = await saveAttempt(quizId, answers);
        if (resultEl) resultEl.textContent = `${t("score", "Score")}: ${result.score}/${result.total}`;
        renderFeedback(result.feedback || []);
        document.querySelectorAll("#quiz input").forEach((input) => {
          input.disabled = true;
        });
        setAttemptStatus(
          result.message || (result.saved ? t("attemptSaved", "Attempt saved.") : t("attemptNotCounted", "Attempt not counted.")),
        );
      } catch (error) {
        checkBtn.disabled = false;
        setAttemptStatus(error?.message ?? t("couldNotSaveAttempt", "Could not save attempt."), true);
      }
    });
  } catch (error) {
    setError(error?.message ?? t("unknownError", "Unknown error"));
  }
});
