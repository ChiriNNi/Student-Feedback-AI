"""Multilingual (English / Russian / Kazakh) sentiment lexicon and default topic taxonomy.

Entries are *stems*: a token matches an entry when the token starts with it
(longest stem wins). Stems shorter than 4 characters only match whole tokens.
This keeps the analyzer light (no model downloads) while handling Russian and
Kazakh word endings reasonably well.
"""

POSITIVE = {
    # English
    "good": 1.6, "great": 2.2, "excellent": 2.8, "amazing": 2.6, "awesome": 2.4, "fantastic": 2.6,
    "clear": 1.5, "clearly": 1.4, "helpful": 1.9, "interesting": 1.7, "useful": 1.7, "love": 2.4, "loved": 2.4,
    "like": 1.0, "liked": 1.3, "enjoy": 1.8, "enjoyed": 1.9, "best": 2.3, "perfect": 2.6, "fair": 1.4,
    "friendly": 1.8, "engaging": 1.9, "organized": 1.5, "well": 0.9, "nice": 1.5, "supportive": 1.9,
    "easy": 1.1, "fast": 1.2, "quick": 1.2, "quickly": 1.2, "comfortable": 1.6, "clean": 1.4, "tasty": 1.8,
    "delicious": 2.2, "modern": 1.3, "responsive": 1.5, "inspiring": 2.2, "knowledgeable": 1.9,
    "recommend": 1.6, "satisfied": 1.7, "improved": 1.3, "convenient": 1.5, "practical": 1.3,
    "valuable": 1.8, "polite": 1.6, "patient": 1.5, "cozy": 1.6, "reliable": 1.6, "affordable": 1.4,
    "thank": 1.3, "thanks": 1.3, "happy": 1.8, "motivat": 1.6, "passionate": 2.0, "structured": 1.3,
    "relevant": 1.2, "brilliant": 2.5, "wonderful": 2.5, "fresh": 1.1, "spacious": 1.3, "quiet": 1.0,
    "understandable": 1.5, "okay": 0.3, "ok": 0.3, "enough": 0.8, "helped": 1.4, "helps": 1.2, "effective": 1.6, "efficient": 1.6, "professional": 1.5, "approachable": 1.7,
    # Russian
    "хорош": 1.6, "отличн": 2.6, "прекрасн": 2.5, "замечательн": 2.5, "интересн": 1.7, "полезн": 1.7,
    "понятн": 1.5, "ясно": 1.2, "нрав": 1.6, "любл": 2.0, "удобн": 1.5, "чист": 1.3, "вкусн": 1.9,
    "быстр": 1.2, "дружелюбн": 1.8, "вежлив": 1.6, "справедлив": 1.5, "помог": 1.5, "помога": 1.5,
    "поддерж": 1.4, "качествен": 1.6, "современ": 1.3, "доступн": 1.1, "рекоменд": 1.5, "довол": 1.7,
    "лучш": 2.0, "супер": 2.0, "класс": 1.8, "спасиб": 1.4, "увлекательн": 2.0, "профессионал": 1.6,
    "организован": 1.4, "структурирован": 1.3, "уютн": 1.6, "свеж": 1.1, "актуальн": 1.2, "эффективн": 1.5,
    "вдохновл": 2.0, "мотивир": 1.6, "приятн": 1.6, "нормальн": 0.3, "достаточно": 0.8,
    # Kazakh
    "жақсы": 1.6, "керемет": 2.5, "тамаша": 2.5, "қызықты": 1.8, "пайдалы": 1.7, "түсінікті": 1.5,
    "ұнады": 1.7, "ұнайды": 1.7, "таза": 1.3, "дәмді": 1.9, "жылдам": 1.2, "тез": 1.0, "ыңғайлы": 1.5,
    "көмектес": 1.5, "сапалы": 1.7, "әділ": 1.4, "сыпайы": 1.6, "қолжетімді": 1.1, "риза": 1.8,
    "үздік": 2.1, "рахмет": 1.4, "жайлы": 1.5, "заманауи": 1.3, "тиімді": 1.5, "кәсіби": 1.5,
}

NEGATIVE = {
    # English
    "bad": -1.8, "poor": -1.8, "poorly": -1.7, "terrible": -2.6, "awful": -2.6, "horrible": -2.6,
    "boring": -1.8, "confusing": -1.8, "confused": -1.4, "unclear": -1.7, "difficult": -1.0, "hard": -0.7,
    "useless": -2.2, "hate": -2.4, "worst": -2.6, "unfair": -2.0, "rude": -2.2, "slow": -1.4, "late": -1.1,
    "broken": -1.9, "outdated": -1.6, "dirty": -1.9, "expensive": -1.3, "crowded": -1.3, "overcrowded": -1.6,
    "noisy": -1.3, "overloaded": -1.8, "overwhelming": -1.7, "stressful": -1.8, "stress": -1.4, "too": -0.6,
    "lack": -1.4, "lacking": -1.4, "missing": -1.2, "problem": -1.3, "problems": -1.3, "issue": -1.1,
    "issues": -1.1, "disorganized": -2.0, "chaotic": -1.9, "cold": -1.0, "unhelpful": -2.0,
    "unresponsive": -1.8, "exhausting": -1.8, "impossible": -1.9, "fail": -1.5, "failed": -1.5,
    "complain": -1.3, "disappointed": -2.0, "disappointing": -2.0, "mess": -1.8, "messy": -1.6,
    "unprofessional": -2.1, "inconsistent": -1.5, "uncomfortable": -1.6, "limited": -1.0, "delay": -1.2,
    "delayed": -1.3, "cancelled": -1.2, "canceled": -1.2, "frustrating": -2.0, "weak": -1.4,
    "waste": -1.9, "ignored": -1.7, "ignore": -1.5, "tasteless": -1.8, "tired": -1.2, "unfriendly": -1.9,
    "unavailable": -1.4, "wait": -0.8, "waiting": -0.9, "queue": -0.9, "queues": -0.9, "overpriced": -1.6,
    "never": -0.8, "heavy": -1.2, "overlap": -0.8, "unbearable": -2.2, "worse": -1.9, "unreliable": -1.7, "irrelevant": -1.4, "monotonous": -1.5, "down": -0.7, "crash": -1.4, "crashes": -1.4,
    "not working": -1.3, "doesn't work": -1.3, "does not work": -1.3,
    # Russian
    "плох": -1.8, "ужасн": -2.6, "скучн": -1.8, "непонятн": -1.8, "сложн": -0.9, "трудн": -0.9,
    "бесполезн": -2.2, "груб": -2.1, "медлен": -1.4, "долго": -1.0, "опаздыв": -1.3, "слома": -1.9,
    "сломан": -1.9, "устарел": -1.6, "грязн": -1.9, "дорог": -1.0, "шумн": -1.3, "перегруж": -1.8,
    "стресс": -1.5, "мало": -0.9, "нехватк": -1.5, "не хватает": -1.5, "проблем": -1.3, "беспоряд": -1.8,
    "хаос": -1.9, "холодн": -1.0, "очеред": -0.9, "разочаров": -2.0, "невкусн": -1.8, "неудобн": -1.6,
    "несправедлив": -2.0, "неорганизов": -2.0, "слаб": -1.3, "отсутств": -1.2, "никогда": -0.8,
    "жалоб": -1.3, "невозможн": -1.9, "тесн": -1.2, "задерж": -1.3, "отмен": -1.1, "слишком": -0.6,
    "хуже": -1.9, "раздража": -1.8, "игнор": -1.7, "устал": -1.2, "нудн": -1.7, "хамств": -2.3,
    "невнимательн": -1.6, "запутан": -1.7, "не работает": -1.4, "висит": -1.0, "тяжел": -1.2, "неинтересн": -1.8, "бестолков": -2.0,
    # Kazakh
    "жаман": -1.9, "нашар": -1.8, "қиын": -0.9, "түсініксіз": -1.8, "қызықсыз": -1.8, "пайдасыз": -2.1,
    "баяу": -1.4, "ұзақ": -0.8, "лас": -1.9, "қымбат": -1.2, "шулы": -1.3, "тым": -0.6, "мәселе": -1.3,
    "проблема": -1.3, "сынған": -1.9, "сынық": -1.8, "ескі": -1.0, "суық": -1.0, "кезек": -0.9,
    "әділетсіз": -2.0, "дөрекі": -2.1, "жетіспе": -1.5, "жоқ": -0.7, "ұнамады": -1.8, "ұнамайды": -1.8,
    "шаршат": -1.5, "ауыр": -1.2, "істемейді": -1.3, "кешігі": -1.3, "кешіктір": -1.3, "тар": -1.0, "қолайсыз": -1.6, "ыңғайсыз": -1.6,
}

LEXICON = {**POSITIVE, **NEGATIVE}

# Words that flip the polarity of the following words (English / Russian)
NEGATIONS_BEFORE = {
    "not", "no", "never", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't", "isnt", "isn't",
    "wasnt", "wasn't", "arent", "aren't", "werent", "weren't", "cant", "can't", "cannot", "wont", "won't",
    "hardly", "without", "не", "нет", "ни", "без",
}
# Kazakh negation follows the word it negates ("жақсы емес" = "not good")
NEGATIONS_AFTER = {"емес"}

# "too fast", "слишком быстро", "тым жылдам": the next opinion word turns negative
EXCESS = {"too", "слишком", "чересчур", "тым"}

INTENSIFIERS = {
    "very": 1.4, "really": 1.3, "extremely": 1.7, "so": 1.2, "super": 1.4, "absolutely": 1.5, "highly": 1.4,
    "incredibly": 1.6, "quite": 1.1, "очень": 1.4, "крайне": 1.6, "весьма": 1.2, "совсем": 1.3,
    "өте": 1.4, "аса": 1.4, "мүлдем": 1.4, "нағыз": 1.3,
}

CONTRAST = {"but", "however", "although", "though", "но", "однако", "зато", "бірақ", "алайда"}

SUGGESTION_MARKERS = (
    "should", "would be better", "would be nice", "would like", "please", "need to", "needs to",
    "recommend", "suggest", "could", "wish", "it would help", "must", "ought", "better if", "add more",
    "надо", "нужно", "следует", "хотелось бы", "предлагаю", "стоит", "было бы", "пожалуйста", "необходимо",
    "лучше бы", "добавить",
    "керек", "қажет", "дұрыс болар", "жақсы болар", "өтінемін", "ұсынамын", "қосу",
)

STOPWORDS = set("""
a an the and or but if then so to of in on at for with from by is are was were be been being it its this that these
those i me my we our you your he she they them their his her as not no do does did have has had can could would should
very really also just more most much many some any all than too about into over after before during there here what
which who whom when where why how only own same other such out up down off again further once both each few nor
will shall may might must am is it's i'm we're they're don't didn't doesn't course class subject teacher university
и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от меня еще
нет о из ему теперь когда даже ну вдруг ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом
себя ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под
будет ж тогда кто этот того потому этого какой совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда
зачем всех никогда можно при наконец два об другой хоть после над больше тот через эти нас про всего них какая много
разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть том нельзя такой им более всегда конечно всю между
очень это курс курса предмет предмета
және мен бен пен да де та те бұл осы сол ол олар біз сіз сен мен бір екі үшін туралы бойынша немесе ма ме ба бе па пе
ғой қой еді болды болып бар жоқ емес өте тым пәні пән курс
""".split())

# Default topic taxonomy (editable by administrators in the UI)
DEFAULT_TOPICS = [
    {
        "name": "Teaching Quality", "color": "#3ef2e0",
        "keywords": ["teach", "lectur", "instructor", "professor", "explain", "explanation", "teacher", "tutor",
                     "преподава", "лектор", "объясня", "объяснен", "учител", "лекци",
                     "мұғалім", "оқытушы", "түсіндір", "дәріс", "ұстаз"],
    },
    {
        "name": "Course Content", "color": "#8b5cff",
        "keywords": ["content", "material", "topic", "syllabus", "curriculum", "practical", "theory", "example",
                     "project", "relevant", "slides",
                     "материал", "содержан", "тема", "темы", "тему", "темат", "программ", "практик", "теори", "пример", "проект", "слайд",
                     "мазмұн", "материалдар", "тақырып", "бағдарлама", "тәжірибе", "мысал", "жоба"],
    },
    {
        "name": "Workload", "color": "#ff4fd8",
        "keywords": ["workload", "homework", "assignment", "deadline", "pace", "load", "tasks", "overload",
                     "нагрузк", "домашн", "задани", "дедлайн", "срок", "темп", "перегруж",
                     "жүктеме", "үй тапсырма", "тапсырма", "мерзім", "дедлайн"],
    },
    {
        "name": "Assessment & Grading", "color": "#ffc857",
        "keywords": ["exam", "grade", "grading", "assessment", "quiz", "test", "midterm", "final", "criteria",
                     "score",
                     "экзамен", "оценк", "оценив", "тест", "контрольн", "критери", "балл", "рубежк",
                     "емтихан", "бағала", "тест", "бақылау", "критерий", "ұпай"],
    },
    {
        "name": "Communication & Organization", "color": "#6fa8ff",
        "keywords": ["schedule", "organiz", "communicat", "announce", "respond", "reply", "email", "timetable",
                     "information", "cancel", "office hours",
                     "расписан", "организац", "общени", "объявлен", "ответ", "информац", "отмен", "связ",
                     "кесте", "ұйымдастыр", "хабарла", "жауап", "ақпарат", "байланыс"],
    },
    {
        "name": "Facilities & Equipment", "color": "#f9a66c",
        "keywords": ["classroom", "room", "lab", "labs", "laborator", "equipment", "projector", "computer", "building", "chair",
                     "heating", "air", "auditorium", "facilit",
                     "аудитори", "кабинет", "лаборатор", "оборудован", "проектор", "компьютер", "здани", "стул",
                     "отоплен", "кондиционер",
                     "аудитория", "сынып", "зертхана", "жабдық", "проектор", "компьютер", "ғимарат", "орындық",
                     "жылыт"],
    },
    {
        "name": "Digital Resources", "color": "#3ef2a0",
        "keywords": ["wifi", "wi-fi", "internet", "lms", "moodle", "portal", "online", "platform", "website",
                     "app", "system", "recording",
                     "интернет", "вайфай", "портал", "онлайн", "платформ", "сайт", "систем", "запис",
                     "интернет", "онлайн", "платформа", "сайт", "жүйе", "жазба"],
    },
    {
        "name": "Staff & Support", "color": "#c792ea",
        "keywords": ["staff", "support", "help desk", "service", "employee", "consult", "advisor", "office",
                     "registrar", "wait", "queue",
                     "сотрудник", "персонал", "поддержк", "обслуживан", "консульт", "офис", "очеред", "ожидан",
                     "қызметкер", "қолдау", "қызмет", "кеңес", "кеңсе", "кезек", "күт"],
    },
    {
        "name": "Food & Cafeteria", "color": "#ff8f70",
        "keywords": ["food", "cafeteria", "canteen", "meal", "menu", "price", "coffee", "lunch", "portion",
                     "еда", "столов", "кафе", "меню", "цена", "цены", "цен", "кофе", "обед", "порци",
                     "тамақ", "асхана", "мәзір", "баға", "кофе", "түскі ас", "порция"],
    },
    {
        "name": "Accommodation", "color": "#7fd8ff",
        "keywords": ["dorm", "dormitory", "hostel", "accommodation", "roommate", "shower", "kitchen", "laundry",
                     "общежит", "комнат", "душ", "кухн", "прачечн", "сосед",
                     "жатақхана", "бөлме", "душ", "ас үй", "кір жуу", "көрші"],
    },
    {
        "name": "Library & Study Space", "color": "#e0d36f",
        "keywords": ["library", "book", "study space", "study room", "reading", "seats", "opening hours", "hours",
                     "библиотек", "книг", "читальн", "мест",
                     "кітапхана", "кітап", "оқу залы", "орын"],
    },
]
