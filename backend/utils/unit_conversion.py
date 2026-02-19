def dms_to_decimal(degrees_str: str) -> float:
    sign_lat = degrees_str[0]
    sign_long = degrees_str[7]
    lat = (
        int(degrees_str[1:3])
        + int(degrees_str[3:5]) / 60
        + int(degrees_str[5:7]) / 3600
    )
    lon = (
        int(degrees_str[8:11])
        + int(degrees_str[11:13]) / 60
        + int(degrees_str[13:15]) / 3600
    )

    if sign_lat == "-":
        lat = -lat
    if sign_long == "-":
        lon = -lon

    return {"lat": lat, "lon": lon}


def strip_empty_fields(record: dict) -> dict:
    filtered_fields = {}
    for key, field in record["fields"].items():
        if field["value"] != "":
            filtered_fields[key] = field
    record["fields"] = filtered_fields
    return record
