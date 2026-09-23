def language_code(value):
    aliases = {'ja':'ja', 'Japanese':'ja', 'Japonês':'ja',
               'ch_sim':'ch_sim', 'zh':'ch_sim', 'Chinese':'ch_sim', 'Chinês':'ch_sim'}
    return aliases.get(value, 'ja')
