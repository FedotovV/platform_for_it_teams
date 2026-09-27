KIND = {
    "survey": "опрос",
    "review": "ревью",
    "retro": "ретро",
}

CYCLE_STATUS = {
    "draft": "черновик",
    "collect": "сбор",
    "review": "разбор",
    "closed": "закрыт",
}

PROBLEM_STATUS = {
    "raised": "поднята",
    "discussing": "на обсуждении",
    "in_progress": "в работе",
    "closed": "закрыта",
}

ACTION_STATUS = {
    "assigned": "назначено",
    "doing": "делается",
    "done": "сделано",
    "not_done": "не сделано",
}

SOURCE = {
    "survey": "опрос",
    "review": "ревью",
    "manual": "ручное опасение",
    "retro": "ретроспектива",
}

ROLE = {
    "manager": "менеджер",
    "leader": "лидер",
    "member": "участник",
    "facilitator": "фасилитатор",
}

ACTION_NAME = {
    "create_cycle": "создать цикл",
    "advance_cycle": "перевести статус цикла",
    "set_survey_interval": "настроить интервал опроса",
}

LINK_KIND = {
    "raised": "поднята в цикле",
    "carried": "перенесена в цикл",
}

NEXT_STATUS = {
    "draft": "Перевести в сбор",
    "collect": "Перевести в разбор",
    "review": "Закрыть",
}

STATUS_BY_ENTITY = {
    "cycle": CYCLE_STATUS,
    "problem": PROBLEM_STATUS,
    "action": ACTION_STATUS,
}
