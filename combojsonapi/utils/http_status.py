from http import HTTPStatus


status = {
    status: {status.value: {"description": status.name.replace("_", " ").capitalize()}}
    for status in HTTPStatus
}

status[HTTPStatus.OK][HTTPStatus.OK.value]["description"] = "Success"
