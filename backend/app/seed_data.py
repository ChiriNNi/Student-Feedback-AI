"""Comment templates used to generate realistic multilingual demo feedback."""

T = {
    "Teaching Quality": {
        "en": {
            "pos": ["The instructor explains complex ideas very clearly.",
                    "Great lecturer, always well prepared and really engaging.",
                    "The teacher is passionate and supportive, I enjoyed every lecture.",
                    "Lectures were clear and the professor answered all our questions patiently.",
                    "Excellent teaching, the instructor is knowledgeable and approachable."],
            "neg": ["The lecturer reads from the slides and the explanations are confusing.",
                    "Lectures are boring and the instructor rarely answers questions.",
                    "The teacher explains too fast and the lectures are hard to follow.",
                    "Poor teaching, the professor often comes late and seems unprepared."],
            "neu": ["The lectures were okay, nothing special.",
                    "The instructor follows the textbook closely."],
        },
        "ru": {
            "pos": ["Преподаватель очень понятно объясняет материал.",
                    "Отличный лектор, лекции интересные и хорошо структурированы.",
                    "Преподаватель всегда помогает и отвечает на вопросы, спасибо!"],
            "neg": ["Преподаватель объясняет непонятно, лекции скучные.",
                    "Лектор просто читает слайды, объяснения запутанные.",
                    "Преподаватель часто опаздывает и плохо готовится к занятиям."],
            "neu": ["Лекции проходят нормально, по учебнику."],
        },
        "kk": {
            "pos": ["Мұғалім материалды өте түсінікті түсіндіреді.",
                    "Оқытушы керемет, дәрістер қызықты өтеді.",
                    "Ұстаз әрқашан көмектеседі, рахмет!"],
            "neg": ["Мұғалім түсініксіз түсіндіреді, дәрістер қызықсыз.",
                    "Оқытушы тым жылдам түсіндіреді, түсіну қиын."],
            "neu": ["Дәрістер оқулық бойынша өтеді."],
        },
    },
    "Course Content": {
        "en": {
            "pos": ["The course content is relevant and very practical.",
                    "Useful material with great real-world examples and projects.",
                    "The projects helped me understand how the theory works in practice."],
            "neg": ["The course material is outdated and not relevant to industry.",
                    "Too much theory and almost no practical examples.",
                    "The slides are outdated and the topics feel disconnected."],
            "neu": ["The syllabus covers the standard topics."],
        },
        "ru": {
            "pos": ["Материал курса актуальный и полезный, много практики.",
                    "Интересные проекты и хорошие примеры из реальной жизни."],
            "neg": ["Материал устаревший, мало практических примеров.",
                    "Слишком много теории, темы плохо связаны между собой."],
            "neu": ["Программа курса стандартная."],
        },
        "kk": {
            "pos": ["Курс мазмұны пайдалы, тәжірибе көп.",
                    "Жобалар қызықты, мысалдар өте пайдалы."],
            "neg": ["Материалдар ескі, тәжірибелік мысалдар жоқ.",
                    "Теория тым көп, тәжірибе жетіспейді."],
            "neu": ["Бағдарлама стандартты тақырыптарды қамтиды."],
        },
    },
    "Workload": {
        "en": {
            "pos": ["The workload is fair and the deadlines are well spaced.",
                    "Homework assignments are manageable and really useful."],
            "neg": ["The workload is too heavy and deadlines overlap with other courses.",
                    "Too many assignments every week, it is very stressful.",
                    "Homework takes too much time, the workload is overwhelming."],
            "neu": ["There are weekly assignments and one project."],
        },
        "ru": {
            "pos": ["Нагрузка нормальная, сроки заданий удобные."],
            "neg": ["Слишком большая нагрузка, дедлайны постоянно пересекаются.",
                    "Очень много домашних заданий, это стресс."],
            "neu": ["Каждую неделю есть домашнее задание."],
        },
        "kk": {
            "pos": ["Жүктеме қалыпты, тапсырма мерзімдері ыңғайлы."],
            "neg": ["Жүктеме тым ауыр, дедлайндар бір уақытқа түседі.",
                    "Үй тапсырмалары тым көп, шаршатады."],
            "neu": ["Әр апта сайын тапсырма беріледі."],
        },
    },
    "Assessment & Grading": {
        "en": {
            "pos": ["Grading is fair and the criteria are clear from the start.",
                    "The exams were fair and matched what we studied.",
                    "Quick and helpful feedback on quizzes and assignments."],
            "neg": ["Grading criteria are unclear and the exam was unfair.",
                    "The midterm had questions we never covered, very unfair.",
                    "Grades are published late and there is no feedback on mistakes."],
            "neu": ["Assessment includes a midterm, a final exam and quizzes."],
        },
        "ru": {
            "pos": ["Оценивание справедливое, критерии понятные.",
                    "Экзамен был справедливым и соответствовал материалу."],
            "neg": ["Критерии оценки непонятные, экзамен был несправедливым.",
                    "Оценки выставляют с задержкой, нет обратной связи."],
            "neu": ["Есть рубежный контроль и финальный экзамен."],
        },
        "kk": {
            "pos": ["Бағалау әділ, критерийлер түсінікті.",
                    "Емтихан әділ өтті."],
            "neg": ["Бағалау критерийі түсініксіз, емтихан әділетсіз болды.",
                    "Ұпайлар кешігіп қойылады, бағалау түсініксіз."],
            "neu": ["Аралық бақылау және қорытынды емтихан бар."],
        },
    },
    "Communication & Organization": {
        "en": {
            "pos": ["Everything is well organized and announcements come on time.",
                    "The instructor responds to emails quickly and the schedule is clear."],
            "neg": ["Classes are often cancelled without any announcement.",
                    "The schedule changes all the time and communication is poor.",
                    "Emails are ignored and information about deadlines is unclear."],
            "neu": ["Announcements are posted on the portal."],
        },
        "ru": {
            "pos": ["Всё хорошо организовано, информацию сообщают вовремя."],
            "neg": ["Занятия часто отменяют без объявления, расписание хаос.",
                    "На письма не отвечают, информация о сроках непонятная."],
            "neu": ["Объявления публикуются на портале."],
        },
        "kk": {
            "pos": ["Барлығы жақсы ұйымдастырылған, ақпарат уақытында беріледі."],
            "neg": ["Сабақ кестесі жиі өзгереді, ақпарат жоқ.",
                    "Хаттарға жауап жоқ, ұйымдастыру нашар."],
            "neu": ["Хабарландырулар порталда жарияланады."],
        },
    },
    "Facilities & Equipment": {
        "en": {
            "pos": ["The classrooms are modern and comfortable.",
                    "The lab equipment is new and works well."],
            "neg": ["The projector in the classroom is often broken.",
                    "Lab computers are outdated and very slow.",
                    "The room is overcrowded and there is no air conditioning."],
            "neu": ["Classes take place in the main building."],
        },
        "ru": {
            "pos": ["Аудитории современные и удобные."],
            "neg": ["Проектор в аудитории постоянно сломан.",
                    "Компьютеры в лаборатории устаревшие и медленные, в аудитории тесно."],
            "neu": ["Занятия проходят в главном здании."],
        },
        "kk": {
            "pos": ["Аудиториялар заманауи және ыңғайлы."],
            "neg": ["Аудиториядағы проектор жиі сынған.",
                    "Зертханадағы компьютерлер ескі және баяу."],
            "neu": ["Сабақтар бас ғимаратта өтеді."],
        },
    },
    "Digital Resources": {
        "en": {
            "pos": ["All materials are available online and the portal works well.",
                    "Lecture recordings on the platform are really helpful.",
                    "The Wi-Fi is fast and reliable now."],
            "neg": ["The Wi-Fi is very slow and keeps disconnecting.",
                    "The online portal is often down before deadlines.",
                    "Materials are uploaded to the platform late."],
            "neu": ["Materials are shared through the LMS."],
        },
        "ru": {
            "pos": ["Все материалы доступны онлайн, портал работает хорошо."],
            "neg": ["Интернет очень медленный, вайфай постоянно отключается.",
                    "Портал не работает перед дедлайнами, это ужасно."],
            "neu": ["Материалы выкладывают на платформу."],
        },
        "kk": {
            "pos": ["Барлық материалдар онлайн қолжетімді, платформа жақсы жұмыс істейді."],
            "neg": ["Интернет өте баяу, жиі үзіледі.",
                    "Платформа дедлайн алдында жұмыс істемейді."],
            "neu": ["Материалдар платформаға жүктеледі."],
        },
    },
    "Staff & Support": {
        "en": {
            "pos": ["The staff are friendly and helpful, the service is fast.",
                    "Support staff solved my problem quickly, very professional.",
                    "Polite staff and almost no waiting time."],
            "neg": ["The staff are rude and the waiting time is too long.",
                    "Long queues and nobody answers the phone.",
                    "I waited for weeks for a simple request, very frustrating."],
            "neu": ["The office is open on weekdays."],
        },
        "ru": {
            "pos": ["Сотрудники вежливые и быстро помогают."],
            "neg": ["Сотрудники грубые, очередь очень долго.",
                    "Долго ждать ответа, обслуживание медленное."],
            "neu": ["Офис работает по будням."],
        },
        "kk": {
            "pos": ["Қызметкерлер сыпайы, тез көмектеседі."],
            "neg": ["Қызметкерлер дөрекі, кезек өте ұзақ.",
                    "Жауап күту тым ұзақ, қызмет баяу."],
            "neu": ["Кеңсе жұмыс күндері ашық."],
        },
    },
    "Food & Cafeteria": {
        "en": {
            "pos": ["The cafeteria food is tasty and fresh.",
                    "Good menu with affordable prices."],
            "neg": ["Food prices in the cafeteria are too expensive for students.",
                    "The canteen is overcrowded at lunch and the food is tasteless.",
                    "The menu is limited and portions are small for the price."],
            "neu": ["The cafeteria is open from 8 to 18."],
        },
        "ru": {
            "pos": ["В столовой вкусная и свежая еда."],
            "neg": ["Цены в столовой слишком дорогие, еда невкусная.",
                    "В обед огромная очередь в столовой, меню однообразное и плохое."],
            "neu": ["Столовая работает с 8 до 18."],
        },
        "kk": {
            "pos": ["Асханадағы тамақ дәмді және таза."],
            "neg": ["Асханада баға тым қымбат, тамақ дәмді емес.",
                    "Түскі асқа кезек ұзақ, мәзір нашар."],
            "neu": ["Асхана 8-ден 18-ге дейін жұмыс істейді."],
        },
    },
    "Accommodation": {
        "en": {
            "pos": ["The dormitory is clean and comfortable.",
                    "Nice dorm rooms and a friendly atmosphere."],
            "neg": ["The dormitory rooms are cold and the showers are broken.",
                    "The dorm kitchen is dirty and the laundry never works.",
                    "Too many roommates in one small room, it is uncomfortable."],
            "neu": ["The dormitory is ten minutes from campus."],
        },
        "ru": {
            "pos": ["В общежитии чисто и уютно."],
            "neg": ["В общежитии холодно, душ сломан.",
                    "Кухня в общежитии грязная, прачечная не работает."],
            "neu": ["Общежитие находится рядом с кампусом."],
        },
        "kk": {
            "pos": ["Жатақхана таза және жайлы."],
            "neg": ["Жатақханадағы бөлмелер суық, душ сынған.",
                    "Жатақханада ас үй лас, кір жуу жұмыс істемейді."],
            "neu": ["Жатақхана кампусқа жақын."],
        },
    },
    "Library & Study Space": {
        "en": {
            "pos": ["The library is quiet and has a great collection of books.",
                    "Great study rooms and helpful librarians."],
            "neg": ["There are not enough seats in the library during exams.",
                    "Library opening hours are too limited on weekends."],
            "neu": ["The library is on the second floor."],
        },
        "ru": {
            "pos": ["В библиотеке тихо и много хороших книг."],
            "neg": ["В библиотеке мало мест во время сессии.",
                    "Библиотека работает слишком мало по выходным."],
            "neu": ["Библиотека находится на втором этаже."],
        },
        "kk": {
            "pos": ["Кітапхана тыныш, кітаптар көп және сапалы."],
            "neg": ["Емтихан кезінде кітапханада орын жетіспейді."],
            "neu": ["Кітапхана екінші қабатта орналасқан."],
        },
    },
}

SUGGESTIONS = {
    "Teaching Quality": {
        "en": ["It would be better if the instructor gave more examples during lectures.",
               "Please record the lectures so we can review them."],
        "ru": ["Хотелось бы больше примеров на лекциях."],
        "kk": ["Дәрісте мысалдарды көбірек келтіру керек."],
    },
    "Course Content": {
        "en": ["The course should include more practical labs and real projects.",
               "Please update the slides with current industry examples."],
        "ru": ["Нужно добавить больше практических заданий."],
        "kk": ["Тәжірибелік сабақтарды көбейту керек."],
    },
    "Workload": {
        "en": ["Deadlines should be coordinated with other courses.",
               "Please reduce the number of weekly assignments."],
        "ru": ["Нужно согласовать дедлайны с другими курсами."],
        "kk": ["Дедлайндарды басқа пәндермен келісу керек."],
    },
    "Assessment & Grading": {
        "en": ["Please publish grading rubrics before each assignment.",
               "It would help to get feedback on exam mistakes."],
        "ru": ["Хотелось бы получать разбор ошибок после экзамена."],
        "kk": ["Бағалау критерийлерін алдын ала жариялау керек."],
    },
    "Communication & Organization": {
        "en": ["Please announce schedule changes at least one day in advance."],
        "ru": ["Нужно заранее сообщать об изменениях в расписании."],
        "kk": ["Кесте өзгерістері туралы алдын ала хабарлау керек."],
    },
    "Facilities & Equipment": {
        "en": ["The university should replace the old projectors and lab computers."],
        "ru": ["Нужно заменить старые компьютеры в лабораториях."],
        "kk": ["Зертханадағы ескі компьютерлерді ауыстыру керек."],
    },
    "Digital Resources": {
        "en": ["The university should improve the Wi-Fi in all buildings."],
        "ru": ["Нужно улучшить интернет во всех корпусах."],
        "kk": ["Барлық ғимаратта интернетті жақсарту керек."],
    },
    "Staff & Support": {
        "en": ["Please add an online booking system to reduce queues."],
        "ru": ["Нужно сделать онлайн-запись, чтобы не стоять в очереди."],
        "kk": ["Кезекті азайту үшін онлайн жазылу қажет."],
    },
    "Food & Cafeteria": {
        "en": ["The cafeteria should offer a cheaper student lunch menu."],
        "ru": ["Нужно сделать недорогое студенческое меню."],
        "kk": ["Студенттерге арзан мәзір қосу керек."],
    },
    "Accommodation": {
        "en": ["The dormitory needs repairs in the showers and heating."],
        "ru": ["В общежитии нужно отремонтировать душ и отопление."],
        "kk": ["Жатақханада душ пен жылытуды жөндеу керек."],
    },
    "Library & Study Space": {
        "en": ["The library should stay open longer during exam weeks."],
        "ru": ["Библиотека должна работать дольше во время сессии."],
        "kk": ["Емтихан кезінде кітапхана ұзағырақ жұмыс істеуі керек."],
    },
}

DEPARTMENTS = [
    ("ENS", "Faculty of Engineering and Natural Sciences"),
    ("BS", "SDU Business School"),
    ("EH", "Faculty of Education and Humanities"),
    ("LSS", "Faculty of Law and Social Sciences"),
]

FACULTY = [
    # email, name, department code
    ("faculty@sdu.edu.kz", "Dr. Aigerim Nurlanovna", "ENS"),
    ("b.serikov@sdu.edu.kz", "Dr. Bauyrzhan Serikov", "ENS"),
    ("d.omarova@sdu.edu.kz", "Dana Omarova", "BS"),
    ("m.karimov@sdu.edu.kz", "Dr. Marat Karimov", "BS"),
    ("s.akhmetova@sdu.edu.kz", "Saule Akhmetova", "EH"),
    ("j.miller@sdu.edu.kz", "John Miller", "EH"),
    ("a.tulegenov@sdu.edu.kz", "Dr. Arman Tulegenov", "LSS"),
    ("g.bekova@sdu.edu.kz", "Gulnara Bekova", "LSS"),
]

COURSES = [
    # code, title, dept, instructor email
    ("CSS 101", "Programming Fundamentals", "ENS", "b.serikov@sdu.edu.kz"),
    ("CSS 212", "Data Structures and Algorithms", "ENS", "faculty@sdu.edu.kz"),
    ("CSS 309", "Machine Learning", "ENS", "faculty@sdu.edu.kz"),
    ("MAT 151", "Calculus I", "ENS", "b.serikov@sdu.edu.kz"),
    ("MGT 201", "Principles of Management", "BS", "d.omarova@sdu.edu.kz"),
    ("FIN 210", "Corporate Finance", "BS", "m.karimov@sdu.edu.kz"),
    ("MKT 220", "Digital Marketing", "BS", "d.omarova@sdu.edu.kz"),
    ("ACC 101", "Financial Accounting", "BS", "m.karimov@sdu.edu.kz"),
    ("EDU 110", "Educational Psychology", "EH", "s.akhmetova@sdu.edu.kz"),
    ("ENG 105", "Academic English", "EH", "j.miller@sdu.edu.kz"),
    ("KAZ 101", "Kazakh Language", "EH", "s.akhmetova@sdu.edu.kz"),
    ("HIS 101", "History of Kazakhstan", "EH", "j.miller@sdu.edu.kz"),
    ("LAW 201", "Constitutional Law", "LSS", "a.tulegenov@sdu.edu.kz"),
    ("POL 110", "Introduction to Political Science", "LSS", "g.bekova@sdu.edu.kz"),
    ("PSY 101", "General Psychology", "LSS", "g.bekova@sdu.edu.kz"),
    ("LAW 305", "International Law", "LSS", "a.tulegenov@sdu.edu.kz"),
]

SERVICES = [
    ("Library", "Academic", ["Library & Study Space", "Staff & Support", "Digital Resources"]),
    ("Dormitory", "Housing", ["Accommodation", "Staff & Support", "Facilities & Equipment"]),
    ("Cafeteria", "Food", ["Food & Cafeteria", "Staff & Support"]),
    ("IT Help Desk", "Technology", ["Digital Resources", "Staff & Support"]),
    ("Registrar Office", "Administration", ["Staff & Support", "Communication & Organization"]),
    ("Sports Center", "Student Life", ["Facilities & Equipment", "Staff & Support"]),
    ("Career Center", "Student Life", ["Staff & Support", "Communication & Organization"]),
    ("Medical Center", "Health", ["Staff & Support", "Facilities & Equipment"]),
]

SEMESTERS = ["Fall 2024", "Spring 2025", "Fall 2025", "Spring 2026", "Fall 2026"]
