def language_code(value):
    aliases = {'ja':'ja', 'Japanese':'ja', 'Japonês':'ja',
               'ch_sim':'ch_sim', 'ch_tra':'ch_tra', 'Chinese (Traditional)':'ch_tra', 'Chinese (Simplified)':'ch_sim', 'zh':'ch_sim', 'Chinese':'ch_sim', 'Chinês':'ch_sim'}
    return aliases.get(value, 'ja')
