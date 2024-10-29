from civil_society_vote.common.contants import GIBIBYTE, KIBIBYTE, MEBIBYTE, TEBIBYTE


def get_human_readable_size(num_bytes: int):
    if num_bytes >= TEBIBYTE:
        size_unit = "TB"
        size_in_unit = num_bytes / TEBIBYTE
    elif num_bytes >= GIBIBYTE:
        size_unit = "GB"
        size_in_unit = num_bytes / GIBIBYTE
    elif num_bytes >= MEBIBYTE:
        size_unit = "MB"
        size_in_unit = num_bytes / MEBIBYTE
    elif num_bytes >= KIBIBYTE:
        size_unit = "KB"
        size_in_unit = num_bytes / KIBIBYTE
    else:
        size_unit = "B"
        size_in_unit = num_bytes

    return {"size": size_in_unit, "unit": size_unit}
