def format_min_sec(seconds: int) -> str:
    min, sec = divmod(seconds, 60)
    return '%02d.%02d' % (min, sec)

def format_elapsed_time_text(elapsed: int, duration: int) -> str:
    if duration != 0 and elapsed <= duration:
      percentage = round(elapsed / duration * 100)
    else:
      percentage = ''
    elapsed_text = format_min_sec(elapsed).rjust(6,' ')
    percentage_text = str(percentage).rjust(3,' ')
    return ' '+elapsed_text+'  '+percentage_text+' '