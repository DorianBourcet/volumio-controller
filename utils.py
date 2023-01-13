def format_min_sec(seconds: int) -> str:
    min, sec = divmod(seconds, 60)
    return '%02d.%02d' % (min, sec)
