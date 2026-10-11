(function () {
  "use strict";

  const TEXT = {
    en: {
      service_name: "Student Feedback",
      admin_panel: "Administration",
      responses: "Responses",
      hero_title: "Your feedback improves the university",
      hero_lead: "Evaluate courses and university services in a few clear steps. Your answers are anonymous.",
      sign_in: "Sign in",
      sign_in_sub: "Use your university account to continue.",
      login_label: "Student ID or email",
      password: "Password",
      remember: "Remember me",
      forgot: "Forgot password?",
      privacy_short: "Personal data is removed before feedback is saved.",
      new_student: "New student?",
      create_account: "Create an account",
      share_feedback: "Choose a course",
      anonymous_title: "Anonymous feedback",
      anonymous_text: "Names, IDs, email addresses and phone numbers are removed before saving.",
      optional: "optional",
      pii_note: "Names, emails and phone numbers are removed automatically.",
      back: "Back",
      continue: "Continue",
      submit_anonymous: "Submit anonymously",
      profile: "Profile",
      sign_out: "Sign out",
      create_account_title: "Create account",
      create_account_sub: "Student self-registration. Staff accounts are created by an administrator.",
      full_name: "Full name",
      student_id: "Student ID",
      university_email: "University email",
      department: "Department",
      confirm_password: "Confirm password",
      already_account: "Already have an account?",
      demo_title: "Demo accounts",
      demo_hint: "Select an account to fill in the login. Password:",
      kind_course: "Course evaluations",
      kind_service: "University services",
      search_courses: "Search by course code, title or instructor",
      search_services: "Search university services",
      your_department: "Your department",
      other_departments: "Other departments",
      submitted: "Submitted",
      rate_now: "Give feedback",
      no_open_forms: "There are no open feedback forms right now.",
      no_results: "Nothing matches your search.",
      rated_progress: "{done} of {total} completed",
      all_rated: "All {total} completed — thank you!",
      question_of: "Question {current} of {total}",
      comment_step: "Final step",
      choose_answer: "Select one answer to continue.",
      rating_1: "Strongly disagree",
      rating_2: "Disagree",
      rating_3: "Neutral",
      rating_4: "Agree",
      rating_5: "Strongly agree",
      comment: "Additional comment",
      comment_hint: "Optional — tell us what should stay and what should improve.",
      login_required: "Enter your student ID or university email.",
      login_invalid: "Enter a 9-digit student ID or a valid email.",
      password_required: "Enter your password.",
      signed_out: "You have been signed out.",
      theme_light: "Use light theme",
      theme_dark: "Use dark theme",
      language: "Language",
      instructor: "Instructor",
      settings: "Settings",
      appearance: "Appearance",
      light: "Light",
      dark: "Dark"
    },
    ru: {
      service_name: "Отзывы студентов",
      admin_panel: "Администрирование",
      responses: "Ответы",
      hero_title: "Ваш отзыв помогает улучшать университет",
      hero_lead: "Оцените учебные курсы и университетские службы за несколько понятных шагов. Ответы анонимны.",
      sign_in: "Войти",
      sign_in_sub: "Используйте университетскую учётную запись.",
      login_label: "Student ID или электронная почта",
      password: "Пароль",
      remember: "Запомнить меня",
      forgot: "Забыли пароль?",
      privacy_short: "Личные данные удаляются до сохранения отзыва.",
      new_student: "Новый студент?",
      create_account: "Создать аккаунт",
      share_feedback: "Выберите курс",
      anonymous_title: "Анонимный отзыв",
      anonymous_text: "Имена, ID, почта и номера телефонов удаляются до сохранения.",
      optional: "необязательно",
      pii_note: "Имена, адреса электронной почты и номера телефонов удаляются автоматически.",
      back: "Назад",
      continue: "Продолжить",
      submit_anonymous: "Отправить анонимно",
      profile: "Профиль",
      sign_out: "Выйти",
      create_account_title: "Создание аккаунта",
      create_account_sub: "Самостоятельная регистрация доступна студентам. Аккаунты сотрудников создаёт администратор.",
      full_name: "Полное имя",
      student_id: "Student ID",
      university_email: "Университетская почта",
      department: "Факультет",
      confirm_password: "Повторите пароль",
      already_account: "Уже есть аккаунт?",
      demo_title: "Демонстрационные аккаунты",
      demo_hint: "Выберите аккаунт для заполнения логина. Пароль:",
      kind_course: "Учебные курсы",
      kind_service: "Службы университета",
      search_courses: "Поиск по коду, названию или преподавателю",
      search_services: "Поиск университетской службы",
      your_department: "Ваш факультет",
      other_departments: "Другие факультеты",
      submitted: "Отправлено",
      rate_now: "Оставить отзыв",
      no_open_forms: "Сейчас нет открытых форм обратной связи.",
      no_results: "По вашему запросу ничего не найдено.",
      rated_progress: "Заполнено: {done} из {total}",
      all_rated: "Все {total} заполнены — спасибо!",
      question_of: "Вопрос {current} из {total}",
      comment_step: "Последний шаг",
      choose_answer: "Выберите один вариант, чтобы продолжить.",
      rating_1: "Полностью не согласен",
      rating_2: "Не согласен",
      rating_3: "Нейтрально",
      rating_4: "Согласен",
      rating_5: "Полностью согласен",
      comment: "Дополнительный комментарий",
      comment_hint: "Необязательно — напишите, что стоит сохранить и что нужно улучшить.",
      login_required: "Введите Student ID или университетскую почту.",
      login_invalid: "Введите Student ID из 9 цифр или корректную почту.",
      password_required: "Введите пароль.",
      signed_out: "Вы вышли из системы.",
      theme_light: "Включить светлую тему",
      theme_dark: "Включить тёмную тему",
      language: "Язык",
      instructor: "Преподаватель",
      settings: "Настройки",
      appearance: "Оформление",
      light: "Светлая",
      dark: "Тёмная"
    },
    kk: {
      service_name: "Студент пікірі",
      admin_panel: "Әкімшілік басқару",
      responses: "Жауаптар",
      hero_title: "Сіздің пікіріңіз университетті жақсартады",
      hero_lead: "Пәндер мен университет қызметтерін бірнеше түсінікті қадаммен бағалаңыз. Жауаптар жасырын сақталады.",
      sign_in: "Кіру",
      sign_in_sub: "Университеттік тіркелгіңізді пайдаланыңыз.",
      login_label: "Student ID немесе электрондық пошта",
      password: "Құпиясөз",
      remember: "Мені есте сақтау",
      forgot: "Құпиясөзді ұмыттыңыз ба?",
      privacy_short: "Жеке деректер пікір сақталмай тұрып жойылады.",
      new_student: "Жаңа студентсіз бе?",
      create_account: "Тіркелгі жасау",
      share_feedback: "Пәнді таңдаңыз",
      anonymous_title: "Жасырын пікір",
      anonymous_text: "Аты-жөн, ID, пошта және телефон нөмірлері сақталмай тұрып жойылады.",
      optional: "міндетті емес",
      pii_note: "Аты-жөн, электрондық пошта және телефон нөмірлері автоматты түрде жойылады.",
      back: "Артқа",
      continue: "Жалғастыру",
      submit_anonymous: "Жасырын жіберу",
      profile: "Профиль",
      sign_out: "Шығу",
      create_account_title: "Тіркелгі жасау",
      create_account_sub: "Өзіндік тіркелу студенттерге арналған. Қызметкерлердің тіркелгісін әкімші жасайды.",
      full_name: "Толық аты-жөні",
      student_id: "Student ID",
      university_email: "Университеттік пошта",
      department: "Факультет",
      confirm_password: "Құпиясөзді қайталаңыз",
      already_account: "Тіркелгіңіз бар ма?",
      demo_title: "Демонстрациялық тіркелгілер",
      demo_hint: "Логинді толтыру үшін тіркелгіні таңдаңыз. Құпиясөз:",
      kind_course: "Оқу пәндері",
      kind_service: "Университет қызметтері",
      search_courses: "Код, атау немесе оқытушы бойынша іздеу",
      search_services: "Университет қызметін іздеу",
      your_department: "Сіздің факультетіңіз",
      other_departments: "Басқа факультеттер",
      submitted: "Жіберілді",
      rate_now: "Пікір қалдыру",
      no_open_forms: "Қазір ашық кері байланыс нысандары жоқ.",
      no_results: "Сұрауыңыз бойынша ештеңе табылмады.",
      rated_progress: "Толтырылды: {done} / {total}",
      all_rated: "Барлығы {total} толтырылды — рақмет!",
      question_of: "{current} / {total} сұрақ",
      comment_step: "Соңғы қадам",
      choose_answer: "Жалғастыру үшін бір жауапты таңдаңыз.",
      rating_1: "Мүлдем келіспеймін",
      rating_2: "Келіспеймін",
      rating_3: "Бейтарап",
      rating_4: "Келісемін",
      rating_5: "Толық келісемін",
      comment: "Қосымша пікір",
      comment_hint: "Міндетті емес — нені сақтау және нені жақсарту керегін жазыңыз.",
      login_required: "Student ID немесе университеттік поштаны енгізіңіз.",
      login_invalid: "9 саннан тұратын Student ID немесе дұрыс пошта енгізіңіз.",
      password_required: "Құпиясөзді енгізіңіз.",
      signed_out: "Сіз жүйеден шықтыңыз.",
      theme_light: "Жарық тақырыпты қосу",
      theme_dark: "Қараңғы тақырыпты қосу",
      language: "Тіл",
      instructor: "Оқытушы",
      settings: "Баптаулар",
      appearance: "Көрініс",
      light: "Жарық",
      dark: "Қараңғы"
    }
  };

  const CONTENT = {
    ru: {
      "Fall 2026": "Осень 2026",
      "Fall 2026 Course Evaluation": "Оценка курсов — осень 2026",
      "Fall 2026 Service Review": "Оценка университетских служб — осень 2026",
      "Rate the courses you took this semester.": "Оцените курсы, которые вы изучали в этом семестре.",
      "Tell university services how they are doing.": "Оцените качество работы университетских служб.",
      "What worked well in this course, and what should be improved?": "Что в этом курсе было полезным и что следует улучшить?",
      "What did you like about this service, and what should change?": "Что вам понравилось в работе службы и что следует изменить?",
      "Clarity": "Понятность",
      "Materials": "Материалы",
      "Workload": "Нагрузка",
      "Assessment": "Оценивание",
      "Overall": "Общая оценка",
      "Staff": "Сотрудники",
      "Availability": "Доступность",
      "Quality": "Качество",
      "The instructor explained the material clearly.": "Преподаватель понятно объяснял материал.",
      "Course materials were useful and up to date.": "Материалы курса были полезными и актуальными.",
      "The workload was reasonable for the credits.": "Учебная нагрузка соответствовала количеству кредитов.",
      "Assessment and grading were fair and transparent.": "Оценивание было справедливым и прозрачным.",
      "Overall, I am satisfied with this course.": "В целом я доволен этим курсом.",
      "Staff were helpful and polite.": "Сотрудники были вежливы и готовы помочь.",
      "The service was available when I needed it.": "Служба была доступна, когда она была мне нужна.",
      "The quality of the service and facilities was good.": "Качество обслуживания и помещений было хорошим.",
      "Overall, I am satisfied with this service.": "В целом я доволен работой этой службы.",
      "Library": "Библиотека",
      "Dormitory": "Общежитие",
      "Cafeteria": "Столовая",
      "Sports Center": "Спортивный центр",
      "IT Help Desk": "Служба IT-поддержки",
      "Registrar's Office": "Офис регистратора",
      "Career Center": "Центр карьеры"
    },
    kk: {
      "Fall 2026": "2026 жылғы күз",
      "Fall 2026 Course Evaluation": "Пәндерді бағалау — 2026 жылғы күз",
      "Fall 2026 Service Review": "Университет қызметтерін бағалау — 2026 жылғы күз",
      "Rate the courses you took this semester.": "Осы семестрде оқыған пәндеріңізді бағалаңыз.",
      "Tell university services how they are doing.": "Университет қызметтерінің жұмысын бағалаңыз.",
      "What worked well in this course, and what should be improved?": "Бұл пәнде не жақсы болды және нені жақсарту керек?",
      "What did you like about this service, and what should change?": "Қызметтің несі ұнады және нені өзгерту керек?",
      "Clarity": "Түсініктілік",
      "Materials": "Материалдар",
      "Workload": "Оқу жүктемесі",
      "Assessment": "Бағалау",
      "Overall": "Жалпы баға",
      "Staff": "Қызметкерлер",
      "Availability": "Қолжетімділік",
      "Quality": "Сапа",
      "The instructor explained the material clearly.": "Оқытушы материалды түсінікті түсіндірді.",
      "Course materials were useful and up to date.": "Пән материалдары пайдалы әрі өзекті болды.",
      "The workload was reasonable for the credits.": "Оқу жүктемесі кредит санына сай болды.",
      "Assessment and grading were fair and transparent.": "Бағалау әділ әрі ашық болды.",
      "Overall, I am satisfied with this course.": "Жалпы алғанда, мен бұл пәнге ризамын.",
      "Staff were helpful and polite.": "Қызметкерлер сыпайы болды және көмектесті.",
      "The service was available when I needed it.": "Қызмет қажет кезде қолжетімді болды.",
      "The quality of the service and facilities was good.": "Қызмет көрсету мен жағдайдың сапасы жақсы болды.",
      "Overall, I am satisfied with this service.": "Жалпы алғанда, мен бұл қызметке ризамын.",
      "Library": "Кітапхана",
      "Dormitory": "Жатақхана",
      "Cafeteria": "Асхана",
      "Sports Center": "Спорт орталығы",
      "IT Help Desk": "IT қолдау қызметі",
      "Registrar's Office": "Тіркеуші кеңсесі",
      "Career Center": "Мансап орталығы"
    }
  };

  const safeStored = (key) => {
    try { return localStorage.getItem(key); } catch { return null; }
  };
  let language = safeStored("sdu.ui.language") || "en";
  if (!TEXT[language]) language = "en";

  function text(key, vars = {}) {
    let value = TEXT[language]?.[key] || TEXT.en[key] || key;
    Object.entries(vars).forEach(([name, replacement]) => {
      value = value.replaceAll(`{${name}}`, String(replacement));
    });
    return value;
  }

  function content(value) {
    return CONTENT[language]?.[value] || value;
  }

  window.uiText = text;
  window.uiContent = content;
  window.getUiLanguage = () => language;

  function preferencesMarkup() {
    return `<div class="preference-block">
      <label>${text("language")}
        <select data-ui-lang-select aria-label="${text("language")}">
          <option value="en"${language === "en" ? " selected" : ""}>English</option>
          <option value="ru"${language === "ru" ? " selected" : ""}>Русский</option>
          <option value="kk"${language === "kk" ? " selected" : ""}>Қазақша</option>
        </select>
      </label>
      <div class="appearance-control" role="group" aria-label="${text("appearance")}">
        <span>${text("appearance")}</span>
        <button type="button" data-set-theme="light">${text("light")}</button>
        <button type="button" data-set-theme="dark">${text("dark")}</button>
      </div>
    </div>`;
  }

  function toolsMarkup(login = false) {
    if (login) return preferencesMarkup();
    const languageName = { en: "English", ru: "Русский", kk: "Қазақша" }[language];
    return `<div class="header-controls">
      <div class="language-picker">
        <button type="button" class="control-pill" data-language-toggle aria-expanded="false" aria-label="${text("language")}: ${languageName}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>
          <span>${languageName}</span>
          <svg class="chevron" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m5 7.5 5 5 5-5"/></svg>
        </button>
        <div class="language-popover" role="listbox" aria-label="${text("language")}" hidden>
          ${[["en", "English", "EN"], ["ru", "Русский", "RU"], ["kk", "Қазақша", "KZ"]].map(([code, name, short]) =>
            `<button type="button" role="option" data-ui-lang="${code}" aria-selected="${language === code}" class="${language === code ? "on" : ""}"><span>${name}</span><small>${short}</small></button>`
          ).join("")}
        </div>
      </div>
      <button type="button" class="control-pill theme-cycle" data-theme-cycle>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"></svg>
        <span class="theme-cycle-text"></span>
      </button>
    </div>`;
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("sdu.ui.theme", theme); } catch {}
    document.querySelectorAll("[data-set-theme]").forEach(button => {
      const selected = button.dataset.setTheme === theme;
      button.classList.toggle("on", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    document.querySelectorAll("[data-theme-cycle]").forEach(button => {
      button.querySelector(".theme-cycle-text").textContent = text(theme === "dark" ? "dark" : "light");
      button.setAttribute("aria-label", text(theme === "dark" ? "theme_light" : "theme_dark"));
      button.querySelector("svg").innerHTML = theme === "dark"
        ? '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>'
        : '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
    });
  }

  function setText(selector, key) {
    document.querySelectorAll(selector).forEach(el => { el.textContent = text(key); });
  }
  function setPlaceholder(selector, key) {
    document.querySelectorAll(selector).forEach(el => { el.placeholder = text(key); });
  }

  function applyStaticText() {
    document.documentElement.lang = language === "kk" ? "kk" : language;
    document.title = `SDU Feedback — ${text("service_name")}`;
    document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = text(el.dataset.i18n); });
    setText("[data-page-back] .lbl-txt, #admBack .lbl-txt", "profile");
    setText("[data-page-logout] .lbl-txt, #admLogout .lbl-txt", "sign_out");
    setText("#registerView .head h2", "create_account_title");
    setText("#registerView .head .sub", "create_account_sub");
    setText('label[for="regName"] span:first-child', "full_name");
    setText('label[for="regStudentId"] span:first-child', "student_id");
    setText('label[for="regEmail"] span:first-child', "university_email");
    setText('label[for="regDept"] span:first-child', "department");
    setText('label[for="regPassword"] span:first-child', "password");
    setText('label[for="regPassword2"] span:first-child', "confirm_password");
    setText("#toSignIn", "sign_in");
    const already = document.querySelector("#registerView .switch-line");
    if (already?.firstChild) already.firstChild.textContent = `${text("already_account")} `;
    setPlaceholder("#fbSearch", "search_courses");

    const demo = document.querySelector(".demo");
    if (demo) {
      demo.innerHTML = `<button type="button" class="demo-toggle" aria-expanded="false">${text("demo_title")}</button>
        <div class="demo-body" hidden><span>${text("demo_hint")} <b>Pulse#2026</b></span><br>
          <button type="button" data-demo="240103083">student · 240103083</button><br>
          <button type="button" data-demo="faculty@sdu.edu.kz">faculty@sdu.edu.kz</button><br>
          <button type="button" data-demo="manager@sdu.edu.kz">manager@sdu.edu.kz</button><br>
          <button type="button" data-demo="admin@sdu.edu.kz">admin@sdu.edu.kz</button>
        </div>`;
      demo.querySelectorAll("[data-demo]").forEach(button => button.addEventListener("click", () => {
        const login = document.getElementById("login");
        const password = document.getElementById("password");
        login.value = button.dataset.demo;
        password.value = "Pulse#2026";
        login.dispatchEvent(new Event("input", { bubbles: true }));
        password.dispatchEvent(new Event("input", { bubbles: true }));
      }));
    }

    document.querySelectorAll("[data-ui-tools]").forEach(container => {
      container.innerHTML = toolsMarkup(container.classList.contains("login-ui-tools"));
    });
    const theme = document.documentElement.dataset.theme || "light";
    applyTheme(theme);
  }

  function setLanguage(next) {
    if (!TEXT[next] || next === language) return;
    language = next;
    try { localStorage.setItem("sdu.ui.language", language); } catch {}
    applyStaticText();
    window.dispatchEvent(new CustomEvent("ui-language-change", { detail: { language } }));
  }

  document.addEventListener("click", event => {
    const languageOption = event.target.closest("[data-ui-lang]");
    if (languageOption) return setLanguage(languageOption.dataset.uiLang);
    const languageToggle = event.target.closest("[data-language-toggle]");
    if (languageToggle) {
      const panel = languageToggle.nextElementSibling;
      const opening = panel.hidden;
      document.querySelectorAll(".language-popover").forEach(item => { item.hidden = true; });
      document.querySelectorAll("[data-language-toggle]").forEach(item => item.setAttribute("aria-expanded", "false"));
      panel.hidden = !opening;
      languageToggle.setAttribute("aria-expanded", String(opening));
      return;
    }
    if (!event.target.closest(".language-picker")) {
      document.querySelectorAll(".language-popover").forEach(item => { item.hidden = true; });
      document.querySelectorAll("[data-language-toggle]").forEach(item => item.setAttribute("aria-expanded", "false"));
    }
    const themeCycle = event.target.closest("[data-theme-cycle]");
    if (themeCycle) return applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    const themeButton = event.target.closest("[data-set-theme]");
    if (themeButton) return applyTheme(themeButton.dataset.setTheme);
    const settingsButton = event.target.closest("[data-settings-toggle]");
    if (settingsButton) {
      const panel = settingsButton.nextElementSibling;
      const opening = panel.hidden;
      document.querySelectorAll(".settings-popover").forEach(item => { item.hidden = true; });
      document.querySelectorAll("[data-settings-toggle]").forEach(item => item.setAttribute("aria-expanded", "false"));
      panel.hidden = !opening;
      settingsButton.setAttribute("aria-expanded", String(opening));
      return;
    }
    const demoToggle = event.target.closest(".demo-toggle");
    if (demoToggle) {
      const body = demoToggle.nextElementSibling;
      body.hidden = !body.hidden;
      demoToggle.setAttribute("aria-expanded", String(!body.hidden));
    }
  });

  document.addEventListener("change", event => {
    if (event.target.matches("[data-ui-lang-select]")) setLanguage(event.target.value);
  });

  const storedTheme = safeStored("sdu.ui.theme");
  const initialTheme = storedTheme || (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = initialTheme;
  applyStaticText();
})();
