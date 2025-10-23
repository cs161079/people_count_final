def strToInt(strVal):
    try:
        i = int(strVal)
    except ValueError:
        # self.logger.logger.error(f"Not a valid integer value.[{strVal}]")
        raise Exception("Not a valid integer V")
    return i