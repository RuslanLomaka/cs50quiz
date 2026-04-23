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

document.addEventListener("DOMContentLoaded", async () => {
  const titleEl = document.querySelector("#title");
  const quizEl = document.querySelector("#quiz");
  const resultEl = document.querySelector("#result");
  const checkBtn = document.querySelector("#check");
  const attemptCountEl = document.querySelector("#attemptCount");
  const averageScoreEl = document.querySelector("#averageScore");
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

  const setAttemptStatus = (msg, isError = false) => {
    if (!attemptStatusEl) return;
    attemptStatusEl.textContent = msg;
    attemptStatusEl.classList.toggle("text-danger", isError);
    attemptStatusEl.classList.toggle("text-muted", !isError);
  };

  const updateStats = (stats) => {
    if (attemptCountEl && typeof stats.attemptCount !== "undefined") {
      attemptCountEl.textContent = String(stats.attemptCount);
    }
    if (averageScoreEl && typeof stats.averagePercent !== "undefined") {
      averageScoreEl.textContent = `${Number(stats.averagePercent).toFixed(1)}%`;
    }
  };

  const resetQuestionStyles = (card) => {
    card.classList.remove("border-success", "border-danger");
    const cardBody = card.querySelector(".card-body");
    if (cardBody) cardBody.classList.remove("bg-success-subtle", "bg-danger-subtle");

    card.querySelectorAll(".form-check-label").forEach((l) => {
      l.style.fontWeight = "400";
      l.classList.remove("fw-bold", "text-danger", "text-success");
    });
  };

  const markCorrectAnswers = (card) => {
    card.querySelectorAll(".form-check-label").forEach((l) => {
      if (l.dataset.correct === "1") l.classList.add("fw-bold");
    });
  };

  const getChosenLabel = (card) => {
    const checked = card.querySelector("input[type=radio]:checked");
    if (!checked) return null;
    const wrap = checked.closest(".form-check");
    if (!wrap) return null;
    return wrap.querySelector(".form-check-label");
  };

  const saveAttempt = async (quizId, score, total) => {
    const res = await fetch(`/api/quizzes/${quizId}/attempts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken") || "",
      },
      body: JSON.stringify({ score, total }),
    });

    if (!res.ok) {
      throw new Error("Failed to save attempt");
    }

    return res.json();
  };

  const renderSources = (questions) => {
    questions.forEach((question, index) => {
      const card = document.querySelector(`.card[data-qid="${question.id ?? index}"] .card-body`);
      if (!card) return;

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
      card.appendChild(wrap);
    });
  };

  try {
    const quizId = window.QUIZ_ID;
    if (!quizId) throw new Error("QUIZ_ID is missing");

    updateStats({
      attemptCount: window.QUIZ_STATS?.attemptCount ?? 0,
      averagePercent: window.QUIZ_STATS?.averagePercent ?? 0,
    });

    const res = await fetch(`/api/quizzes/${quizId}`);
    if (!res.ok) throw new Error("Failed to load quiz");

    QUIZ = await res.json();

    if (titleEl) titleEl.textContent = QUIZ.title ?? "Quiz";
    if (!quizEl) return;

    quizEl.innerHTML = "";

    (QUIZ.questions ?? []).forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "card shadow-sm";
      card.dataset.qid = q.id ?? idx;

      const body = document.createElement("div");
      body.className = "card-body";

      const qText = document.createElement("div");
      qText.className = "card-title fw-semibold";
      qText.textContent = `${idx + 1}. ${q.question ?? ""}`;
      body.appendChild(qText);

      const answersWrap = document.createElement("div");
      answersWrap.className = "vstack gap-2 mt-3";

      const shuffledAnswers = shuffleArray(q.answers ?? []);

      shuffledAnswers.forEach((a, aIdx) => {
        const id = `q${q.id ?? idx}_a${aIdx}`;

        const wrap = document.createElement("div");
        wrap.className = "form-check";

        const input = document.createElement("input");
        input.className = "form-check-input";
        input.type = "radio";
        input.name = `q_${q.id ?? idx}`;
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
        setAttemptStatus("");

        const total = (QUIZ.questions ?? []).length;
        let correctCount = 0;

        document.querySelectorAll(".card[data-qid]").forEach((card) => {
          resetQuestionStyles(card);
          markCorrectAnswers(card);

          const chosenLabel = getChosenLabel(card);
          if (!chosenLabel) return;

          const isCorrect = chosenLabel.dataset.correct === "1";
          if (isCorrect) {
            correctCount += 1;
            chosenLabel.classList.add("text-success");
            card.classList.add("border-success");
          } else {
            chosenLabel.classList.add("text-danger");
            card.classList.add("border-danger");
          }
        });

        if (resultEl) resultEl.textContent = `Score: ${correctCount}/${total}`;
        renderSources(QUIZ.questions ?? []);

        if (total > 0) {
          try {
            const stats = await saveAttempt(quizId, correctCount, total);
            updateStats(stats);
            setAttemptStatus("Attempt saved.");
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
