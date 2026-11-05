from ..i18n.sync import translate_dictionary
res = translate_dictionary({'saludo': 'Hola {user}'}, 'en', engine='argos')
print(res)
