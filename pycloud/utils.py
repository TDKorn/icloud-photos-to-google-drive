def convert_bytes(bytes, format='MB'):
    formats = {
        'B': 0,
        'KB': 1,
        'MB': 2,
        'GB': 3,
        'TB': 4
    }
    if format not in formats:
        raise ValueError('Not a valid format. Valid formats: {}'.format([f for f in formats]))
    else:
        pwr = formats[format]
        return bytes / (1024 ** pwr)
