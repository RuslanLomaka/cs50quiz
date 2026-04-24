// quizforger/static/quizforger/quiz.js
let QUIZ = null;

function getCookie(name) {
  const cookieValue = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));

  if (!cookieValue) return null;
  return decodeURIComponent(cookieValue.split("=").slice(1).join("="));
}

function shuffleArray(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function answerLetter(index) {
  return String.fromCharCode(65 + index);
}

function normalizeSourceUrl(rawUrl) {
  if (typeof rawUrl !== "string") return "";

  const trimmed = rawUrl.trim();
  const markdownMatch = trimmed.match(/^\[[^\]]*\]\((https?:\/\/[^)\s]+)\)$/i);
  if (markdownMatch) {
    return markdownMatch[1];
  }

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  return "";
}

function correctAnswersCount(question) {
  return (question.answers ?? []).filter((answer) => answer?.correct).length;
}

function isMultipleAnswerQuestion(question) {
  return correctAnswersCount(question) > 1;
}

document.addEventListener("DOMContentLoaded", async () => {
  const titleEl = document.querySelector("#title");
  const quizEl = document.querySelector("#quiz");
  const resultEl = document.querySelector("#result");
  const checkBtn = document.querySelector("#check");
  const attemptStatusEl = document.querySelector("#attemptStatus");

  const setError = (msg) => {
    if (titleEl) titleEl.textContent = "Error";
    if (quizEl) quizEl.textContent = msg;
    if (resultEl) resultEl.textContent = "";
  };

  const clearResult = () => {
    if (resultEl) resultEl.textContent = "";
  };

  const clearSources = () => {
    document.querySelectorAll(".question-sources").forEach((el) => el.remove());
  };

  const clearFeedback = () => {
    document.querySelectorAll(".question-feedback").forEach((el) => el.remove());
  };

  const setAttemptStatus = (msg, isError = false) => {
    if (!attemptStatusEl) return;
    attemptStatusEl.textContent = msg;
    attemptStatusEl.classList.toggle("text-danger", isError);
    attemptStatusEl.classList.toggle("text-muted", !isError);
  };

  const resetQuestionStyles = (card) => {
    card.classList.remove("border-success", "border-danger");

    card.querySelectorAll(".form-check-label").forEach((l) => {
      l.style.fontWeight = "400";
      l.classList.remove("fw-bold", "text-danger", "text-success", "revealed-correct");
    });
  };

  const markCorrectAnswers = (card) => {
    card.querySelectorAll(".form-check-label").forEach((l) => {
      if (l.dataset.correct === "1") l.classList.add("fw-bold", "revealed-correct");
    });
  };

  const getSelectedLabels = (card) => {
    return Array.from(card.querySelectorAll("input:checked"))
      .map((input) => input.closest(".form-check")?.querySelector(".form-check-label"))
      .filter(Boolean);
  };

  const saveAttempt = async (quizId, score, total, answeredCount) => {
    // The backend is the source of truth for attempt counting rules, so the
    // player sends raw stats and then renders whatever summary comes back.
    const res = await fetch(`/api/quizzes/${quizId}/attempts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken") || "",
      },
      body: JSON.stringify({ score, total, answered_count: answeredCount }),
    });

    if (!res.ok) {
      const message = (await res.text()).trim();
      throw new Error(message || "Failed to save attempt");
    }

    return res.json();
  };

  const findQuestionBody = (question, index) => {
    return document.querySelector(`.card[data-qid="${question.id ?? index}"] .card-body`);
  };

  const renderSources = (questions) => {
    questions.forEach((question, index) => {
      const cardBody = findQuestionBody(question, index);
      if (!cardBody) return;

      const sources = (Array.isArray(question.sources) ? question.sources : [])
        .map((source) => ({
          ...source,
          normalizedUrl: normalizeSourceUrl(source?.url),
        }))
        .filter((source) => source.normalizedUrl);

      if (sources.length === 0) return;

      const wrap = document.createElement("div");
      wrap.className = "question-sources border-top mt-3 pt-3";

      const heading = document.createElement("div");
      heading.className = "fw-semibold small text-uppercase text-muted mb-2";
      heading.textContent = "Sources";
      wrap.appendChild(heading);

      const list = document.createElement("div");
      list.className = "vstack gap-2";

      sources.forEach((source, sourceIndex) => {
        const item = document.createElement("div");

        const link = document.createElement("a");
        link.href = source.normalizedUrl;
        link.target = "_blank";
        link.rel = "noreferrer noopener";
        link.textContent = source.title?.trim() || `Source ${sourceIndex + 1}`;
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
      cardBody.appendChild(wrap);
    });
  };

  const renderFeedback = (card, question, status) => {
    const body = card.querySelector(".card-body");
    if (!body) return;

    const correctLabels = Array.from(card.querySelectorAll('.form-check-label[data-correct="1"]'));
    const correctText = correctLabels.map((label) => label.textContent?.trim() || "").filter(Boolean).join("; ");
    const explanation = typeof question.explanation === "string" ? question.explanation.trim() : "";

    let lead;
    if (status === "correct") {
      lead = "You got this right.";
    } else if (status === "missed") {
      lead = `You missed this question. The correct ${correctLabels.length > 1 ? "answers were" : "answer was"}: ${correctText}.`;
    } else {
      lead = `Your answer was not correct. The correct ${correctLabels.length > 1 ? "answers were" : "answer was"}: ${correctText}.`;
    }

    const wrap = document.createElement("div");
    wrap.className = "question-feedback mt-3 pt-3";

    const leadEl = document.createElement("div");
    leadEl.className = `fw-semibold ${status === "correct" ? "text-success" : status === "missed" ? "text-muted" : "text-danger"}`;
    leadEl.textContent = lead;
    wrap.appendChild(leadEl);

    if (explanation) {
      const explanationWrap = document.createElement("div");
      explanationWrap.className = "question-explanation mt-3";

      const explanationTitle = document.createElement("div");
      explanationTitle.className = "small fw-semibold text-uppercase text-muted mb-1";
      explanationTitle.textContent = "Explanation";
      explanationWrap.appendChild(explanationTitle);

      const explanationEl = document.createElement("div");
      explanationEl.className = "small";
      explanationEl.textContent = explanation;
      explanationWrap.appendChild(explanationEl);
      wrap.appendChild(explanationWrap);
    }

    body.appendChild(wrap);
  };

  try {
    const quizId = window.QUIZ_ID;
    if (!quizId) throw new Error("QUIZ_ID is missing");

    const res = await fetch(`/api/quizzes/${quizId}`);
    if (!res.ok) throw new Error("Failed to load quiz");

    QUIZ = await res.json();

    if (titleEl) titleEl.textContent = QUIZ.title ?? "Quiz";
    if (!quizEl) return;

    quizEl.innerHTML = "";

    (QUIZ.questions ?? []).forEach((question, idx) => {
      const card = document.createElement("div");
      card.className = "card shadow-sm";
      card.dataset.qid = question.id ?? idx;

      const body = document.createElement("div");
      body.className = "card-body";

      const qText = document.createElement("div");
      qText.className = "card-title fw-semibold";
      qText.textContent = `${idx + 1}. ${question.question ?? ""}`;
      body.appendChild(qText);

      if (isMultipleAnswerQuestion(question)) {
        const multiNote = document.createElement("div");
        multiNote.className = "small text-muted mt-2";
        multiNote.textContent = "This question has more than 1 correct answer.";
        body.appendChild(multiNote);
      }

      const answersWrap = document.createElement("div");
      answersWrap.className = "vstack gap-2 mt-3";

      // Answers are shuffled on render so imported quizzes do not leak a
      // predictable correct-answer position.
      const shuffledAnswers = shuffleArray(question.answers ?? []);
      const inputType = isMultipleAnswerQuestion(question) ? "checkbox" : "radio";

      shuffledAnswers.forEach((a, aIdx) => {
        const id = `q${question.id ?? idx}_a${aIdx}`;

        const wrap = document.createElement("div");
        wrap.className = "form-check";

        const input = document.createElement("input");
        input.className = "form-check-input";
        input.type = inputType;
        input.name = `q_${question.id ?? idx}`;
        input.id = id;

        const label = document.createElement("label");
        label.className = "form-check-label";
        label.htmlFor = id;
        label.dataset.correct = a.correct ? "1" : "0";
        label.style.fontWeight = "400";
        label.textContent = `${answerLetter(aIdx)}. ${a.text ?? ""}`;

        wrap.appendChild(input);
        wrap.appendChild(label);
        answersWrap.appendChild(wrap);
      });

      body.appendChild(answersWrap);
      card.appendChild(body);
      quizEl.appendChild(card);
    });

    if (checkBtn) {
      checkBtn.addEventListener("click", async () => {
        if (!QUIZ) return;

        clearResult();
        clearSources();
        clearFeedback();
        setAttemptStatus("");

        const total = (QUIZ.questions ?? []).length;
        let correctCount = 0;
        let answeredCount = 0;

        (QUIZ.questions ?? []).forEach((question, questionIndex) => {
          const card = document.querySelector(`.card[data-qid="${question.id ?? questionIndex}"]`);
          if (!card) return;

          resetQuestionStyles(card);
          markCorrectAnswers(card);

          const selectedLabels = getSelectedLabels(card);
          const correctLabels = Array.from(card.querySelectorAll('.form-check-label[data-correct="1"]'));
          const selectedSet = new Set(selectedLabels.map((label) => label.textContent));
          const correctSet = new Set(correctLabels.map((label) => label.textContent));
          const gotAnything = selectedLabels.length > 0;
          if (gotAnything) answeredCount += 1;

          // A multiple-answer question only counts as correct if the selected
          // set matches the correct set exactly.
          const isCorrect =
            gotAnything &&
            selectedSet.size === correctSet.size &&
            Array.from(correctSet).every((text) => selectedSet.has(text));

          if (isCorrect) {
            correctCount += 1;
            selectedLabels.forEach((label) => label.classList.add("text-success"));
            card.classList.add("border-success");
            renderFeedback(card, question, "correct");
          } else {
            selectedLabels.forEach((label) => {
              if (label.dataset.correct === "1") {
                label.classList.add("text-success");
              } else {
                label.classList.add("text-danger");
              }
            });
            card.classList.add("border-danger");
            renderFeedback(card, question, gotAnything ? "wrong" : "missed");
          }
        });

        if (resultEl) resultEl.textContent = `Score: ${correctCount}/${total}`;
        renderSources(QUIZ.questions ?? []);

        if (total > 0) {
          try {
            const stats = await saveAttempt(quizId, correctCount, total, answeredCount);
            setAttemptStatus(stats.message || (stats.saved ? "Attempt saved." : "Attempt not counted."));
          } catch (err) {
            setAttemptStatus(err?.message ?? "Could not save attempt.", true);
          }
        }
      });
    }
  } catch (err) {
    setError(err?.message ?? "Unknown error");
  }
});
