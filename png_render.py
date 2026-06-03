from __future__ import annotations

import struct
import math
import zlib
from functools import lru_cache
from pathlib import Path

from draw_core import ALL_WEATHER


SPRITE_WIDTH = 114
SPRITE_HEIGHT = 129
SPRITE_COUNT = len(ALL_WEATHER)

SPRITE_INDEX = {code: index for index, code in enumerate(ALL_WEATHER)}

FONT_5X7 = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "01010", "00100", "00100", "00100", "01010", "10001"],
    "Y": ["10001", "01010", "00100", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}

FONT_5X7_ROUNDED = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "0": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "00110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
}

FOOTER_FONT_3X5 = {
    " ": ["000", "000", "000", "000", "000"],
    "A": ["010", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "D": ["110", "101", "101", "101", "110"],
    "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"],
    "G": ["011", "100", "101", "101", "011"],
    "H": ["101", "101", "111", "101", "101"],
    "O": ["010", "101", "101", "101", "010"],
    "R": ["110", "101", "110", "101", "101"],
    "S": ["011", "100", "010", "001", "110"],
    "T": ["111", "010", "010", "010", "010"],
    "Y": ["101", "101", "010", "010", "010"],
}


def _draw_micro_text(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int, int],
) -> None:
    cursor_x = x
    for character in text.upper():
        pattern = FOOTER_FONT_3X5.get(character, FOOTER_FONT_3X5[" "])
        for row_index, pattern_row in enumerate(pattern):
            for column_index, bit in enumerate(pattern_row):
                if bit == "1":
                    _set_pixel(pixels, width, height, cursor_x + column_index, y + row_index, color)
        cursor_x += 4



def _decode_png_rgba(png_bytes: bytes) -> tuple[int, int, bytes]:
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid_png_signature")

    offset = 8
    width = height = bit_depth = color_type = compression = filter_method = interlace = None
    idat_chunks = bytearray()

    while offset < len(png_bytes):
        length = struct.unpack_from(">I", png_bytes, offset)[0]
        offset += 4
        chunk_type = png_bytes[offset : offset + 4]
        offset += 4
        chunk_data = png_bytes[offset : offset + length]
        offset += length
        offset += 4

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
        elif chunk_type == b"IDAT":
            idat_chunks.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError("missing_png_header")
    if (bit_depth, color_type, compression, filter_method, interlace) != (8, 6, 0, 0, 0):
        raise ValueError("unsupported_png_format")

    raw = zlib.decompress(bytes(idat_chunks))
    stride = width * 4
    expected_length = height * (stride + 1)
    if len(raw) != expected_length:
        raise ValueError("invalid_png_data")

    output = bytearray(height * stride)
    previous_row = bytearray(stride)
    position = 0
    for row_index in range(height):
        filter_type = raw[position]
        position += 1
        filtered_row = bytearray(raw[position : position + stride])
        position += stride
        output_row = _unfilter_png_row(filter_type, filtered_row, previous_row, 4)
        output[row_index * stride : (row_index + 1) * stride] = output_row
        previous_row = output_row

    return width, height, bytes(output)


def _unfilter_png_row(filter_type: int, row: bytearray, previous_row: bytearray, bytes_per_pixel: int) -> bytearray:
    if filter_type == 0:
        return row

    output = bytearray(len(row))
    if filter_type == 1:
        for index, value in enumerate(row):
            left = output[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            output[index] = (value + left) & 0xFF
        return output

    if filter_type == 2:
        for index, value in enumerate(row):
            output[index] = (value + previous_row[index]) & 0xFF
        return output

    if filter_type == 3:
        for index, value in enumerate(row):
            left = output[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous_row[index]
            output[index] = (value + ((left + up) >> 1)) & 0xFF
        return output

    if filter_type == 4:
        for index, value in enumerate(row):
            left = output[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous_row[index]
            up_left = previous_row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            output[index] = (value + _paeth_predictor(left, up, up_left)) & 0xFF
        return output

    raise ValueError("unsupported_png_filter")


def _paeth_predictor(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    up_left_distance = abs(estimate - up_left)
    if left_distance <= up_distance and left_distance <= up_left_distance:
        return left
    if up_distance <= up_left_distance:
        return up
    return up_left


def _encode_png_rgba(width: int, height: int, pixels: bytes) -> bytes:
    stride = width * 4
    raw = bytearray()
    for row_index in range(height):
        raw.append(0)
        start = row_index * stride
        raw.extend(pixels[start : start + stride])
    compressed = zlib.compress(bytes(raw), level=9)

    def chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
        return (
            struct.pack(">I", len(chunk_data))
            + chunk_type
            + chunk_data
            + struct.pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def _new_canvas(width: int, height: int, color: tuple[int, int, int, int]) -> bytearray:
    pixels = bytearray(width * height * 4)
    r, g, b, a = color
    for index in range(0, len(pixels), 4):
        pixels[index] = r
        pixels[index + 1] = g
        pixels[index + 2] = b
        pixels[index + 3] = a
    return pixels


def _set_pixel(pixels: bytearray, width: int, height: int, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    if x < 0 or y < 0 or x >= width or y >= height:
        return
    index = (y * width + x) * 4
    pixels[index : index + 4] = bytes(color)


def _blend_pixel(pixels: bytearray, width: int, height: int, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    if x < 0 or y < 0 or x >= width or y >= height:
        return

    index = (y * width + x) * 4
    src_r, src_g, src_b, src_a = color
    if src_a >= 255:
        pixels[index] = src_r
        pixels[index + 1] = src_g
        pixels[index + 2] = src_b
        pixels[index + 3] = 255
        return
    if src_a <= 0:
        return

    dst_r = pixels[index]
    dst_g = pixels[index + 1]
    dst_b = pixels[index + 2]
    dst_a = pixels[index + 3]

    alpha = src_a / 255.0
    inv_alpha = 1.0 - alpha
    out_a = int(src_a + dst_a * inv_alpha)
    if out_a <= 0:
        pixels[index + 3] = 0
        return

    pixels[index] = int(src_r * alpha + dst_r * inv_alpha)
    pixels[index + 1] = int(src_g * alpha + dst_g * inv_alpha)
    pixels[index + 2] = int(src_b * alpha + dst_b * inv_alpha)
    pixels[index + 3] = min(out_a, 255)


def _fill_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    color: tuple[int, int, int, int],
) -> None:
    if rect_width <= 0 or rect_height <= 0:
        return

    row_bytes = bytes(color) * rect_width
    row_stride = width * 4
    copy_length = rect_width * 4
    for row in range(y, y + rect_height):
        if row < 0 or row >= height:
            continue
        start = (row * width + x) * 4
        end = start + copy_length
        if start < 0 or end > len(pixels):
            continue
        pixels[start:end] = row_bytes


@lru_cache(maxsize=128)
def _rounded_rect_spans(rect_width: int, rect_height: int, radius: int) -> tuple[tuple[int, int], ...]:
    radius = max(0, min(radius, rect_width // 2, rect_height // 2))
    radius_sq = radius * radius
    spans: list[tuple[int, int]] = []

    for row in range(rect_height):
        if radius == 0 or (radius <= row < rect_height - radius):
            spans.append((0, rect_width))
            continue

        if row < radius:
            dy = (radius - 1) - row
        else:
            dy = row - (rect_height - radius)

        start = None
        for column in range(rect_width):
            dx = 0
            if column < radius:
                dx = (radius - 1) - column
            elif column >= rect_width - radius:
                dx = column - (rect_width - radius)

            if dx * dx + dy * dy <= radius_sq:
                start = column
                break

        if start is None:
            spans.append((0, 0))
            continue

        end = rect_width
        for column in range(rect_width - 1, start - 1, -1):
            dx = 0
            if column < radius:
                dx = (radius - 1) - column
            elif column >= rect_width - radius:
                dx = column - (rect_width - radius)

            if dx * dx + dy * dy <= radius_sq:
                end = column + 1
                break

        spans.append((start, end))

    return tuple(spans)


def _stroke_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    color: tuple[int, int, int, int],
) -> None:
    if rect_width <= 0 or rect_height <= 0:
        return

    top = (y * width + x) * 4
    bottom = ((y + rect_height - 1) * width + x) * 4
    row_bytes = bytes(color) * rect_width
    pixels[top : top + rect_width * 4] = row_bytes
    if rect_height > 1:
        pixels[bottom : bottom + rect_width * 4] = row_bytes

    row_color = bytes(color) * 1
    for row in range(y + 1, y + rect_height - 1):
        if row < 0 or row >= height:
            continue
        left = (row * width + x) * 4
        right = (row * width + x + rect_width - 1) * 4
        if 0 <= left < len(pixels):
            pixels[left : left + 4] = row_color
        if 0 <= right < len(pixels):
            pixels[right : right + 4] = row_color


def _fill_rounded_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    radius: int,
    color: tuple[int, int, int, int],
) -> None:
    spans = _rounded_rect_spans(rect_width, rect_height, radius)
    color_bytes = bytes(color)
    for row_offset, (start_x, end_x) in enumerate(spans):
        if start_x >= end_x:
            continue
        row = y + row_offset
        if row < 0 or row >= height:
            continue
        start = ((row * width) + (x + start_x)) * 4
        length = (end_x - start_x) * 4
        if start < 0 or start + length > len(pixels):
            continue
        pixels[start : start + length] = color_bytes * (end_x - start_x)


def _stroke_rounded_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    radius: int,
    color: tuple[int, int, int, int],
) -> None:
    outer_spans = _rounded_rect_spans(rect_width, rect_height, radius)
    inner_spans = _rounded_rect_spans(rect_width, rect_height, max(radius - 1, 0))
    color_bytes = bytes(color)

    for row_offset, ((outer_start, outer_end), (inner_start, inner_end)) in enumerate(zip(outer_spans, inner_spans)):
        row = y + row_offset
        if row < 0 or row >= height:
            continue

        if outer_start < inner_start:
            start = ((row * width) + (x + outer_start)) * 4
            length = (inner_start - outer_start) * 4
            if start >= 0 and start + length <= len(pixels):
                pixels[start : start + length] = color_bytes * (inner_start - outer_start)

        if inner_end < outer_end:
            start = ((row * width) + (x + inner_end)) * 4
            length = (outer_end - inner_end) * 4
            if start >= 0 and start + length <= len(pixels):
                pixels[start : start + length] = color_bytes * (outer_end - inner_end)


def _draw_text(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int, int],
    scale: int = 2,
    font: dict[str, list[str]] = FONT_5X7,
    edge_alpha: int | None = None,
) -> None:
    cursor_x = x
    for character in text.upper():
        pattern = font.get(character, font[" "])
        for row_index, pattern_row in enumerate(pattern):
            for column_index, bit in enumerate(pattern_row):
                if bit != "1":
                    continue
                pixel_alpha = color[3]
                if edge_alpha is not None:
                    neighbors = 0
                    for neighbor_row, neighbor_col in (
                        (row_index - 1, column_index),
                        (row_index + 1, column_index),
                        (row_index, column_index - 1),
                        (row_index, column_index + 1),
                    ):
                        if 0 <= neighbor_row < len(pattern) and 0 <= neighbor_col < len(pattern[0]):
                            if pattern[neighbor_row][neighbor_col] == "1":
                                neighbors += 1
                    if neighbors <= 2:
                        pixel_alpha = edge_alpha
                for scaled_y in range(scale):
                    for scaled_x in range(scale):
                        _set_pixel(
                            pixels,
                            width,
                            height,
                            cursor_x + column_index * scale + scaled_x,
                            y + row_index * scale + scaled_y,
                            (color[0], color[1], color[2], pixel_alpha),
                        )
        cursor_x += (5 * scale) + scale


def _blit_rgba(
    pixels: bytearray,
    width: int,
    height: int,
    source: bytes,
    source_width: int,
    source_height: int,
    dest_x: int,
    dest_y: int,
) -> None:
    row_length = source_width * 4
    for row in range(source_height):
        target_y = dest_y + row
        if target_y < 0 or target_y >= height:
            continue
        source_index = row * row_length
        target_index = (target_y * width + dest_x) * 4
        end_index = target_index + row_length
        if target_index < 0 or end_index > len(pixels):
            continue
        pixels[target_index:end_index] = source[source_index : source_index + row_length]


@lru_cache(maxsize=1)
def _load_sprite_sheet(sprite_path: str) -> tuple[int, int, bytes]:
    return _decode_png_rgba(Path(sprite_path).read_bytes())


def _extract_sprite_tile(sprite_pixels: bytes, sprite_width: int, index: int) -> bytes:
    start_y = index * SPRITE_HEIGHT
    tile = bytearray(SPRITE_WIDTH * SPRITE_HEIGHT * 4)
    row_stride = sprite_width * 4
    tile_stride = SPRITE_WIDTH * 4
    for row in range(SPRITE_HEIGHT):
        source_start = ((start_y + row) * row_stride)
        destination_start = row * tile_stride
        tile[destination_start : destination_start + tile_stride] = sprite_pixels[
            source_start : source_start + tile_stride
        ]
    return bytes(tile)


def _profile_accent(profile: str) -> tuple[int, int, int, int]:
    if profile == "dry":
        return (255, 187, 102, 255)
    if profile == "equal":
        return (109, 226, 255, 255)
    if profile == "wet":
        return (90, 140, 255, 255)
    return (109, 226, 165, 255)


@lru_cache(maxsize=8)
def _base_canvas_for_slot_count(slot_count: int) -> bytes:
    card_width = 118
    card_height = 160
    label_height = 22
    card_gap = 18
    card_radius = 22
    outer_padding_x = 16
    outer_padding_y = 16
    panel_padding_x = 24
    panel_padding_y = 18
    canvas_width = outer_padding_x * 2 + panel_padding_x * 2 + slot_count * card_width + max(slot_count - 1, 0) * card_gap
    canvas_height = 218
    footer_text = "Created by Gbech for GTSC"
    footer_x = canvas_width - (len(footer_text) * 4) - 6
    footer_y = canvas_height - 11

    pixels = _new_canvas(canvas_width, canvas_height, (8, 16, 26, 255))

    _fill_rect(pixels, canvas_width, canvas_height, 0, 0, canvas_width, canvas_height, (8, 16, 26, 255))
    _fill_rounded_rect(
        pixels,
        canvas_width,
        canvas_height,
        outer_padding_x,
        outer_padding_y,
        canvas_width - outer_padding_x * 2,
        canvas_height - outer_padding_y * 2,
        24,
        (18, 28, 44, 255),
    )
    _stroke_rounded_rect(
        pixels,
        canvas_width,
        canvas_height,
        outer_padding_x,
        outer_padding_y,
        canvas_width - outer_padding_x * 2,
        canvas_height - outer_padding_y * 2,
        24,
        (74, 100, 128, 255),
    )

    card_top = outer_padding_y + panel_padding_y - 6
    for index in range(slot_count):
        card_left = outer_padding_x + panel_padding_x + index * (card_width + card_gap)
        shadow_color = (0, 0, 0, 76)
        _fill_rounded_rect(
            pixels,
            canvas_width,
            canvas_height,
            card_left + 3,
            card_top + 4,
            card_width,
            card_height,
            card_radius,
            shadow_color,
        )
        _fill_rounded_rect(
            pixels,
            canvas_width,
            canvas_height,
            card_left,
            card_top,
            card_width,
            card_height,
            card_radius,
            (16, 22, 34, 255),
        )
        _stroke_rounded_rect(
            pixels,
            canvas_width,
            canvas_height,
            card_left,
            card_top,
            card_width,
            card_height,
            card_radius,
            (84, 100, 120, 255),
        )

        _draw_text(
            pixels,
            canvas_width,
            canvas_height,
            card_left + 23,
            card_top + 138,
            f"Slot {index + 1}",
            (255, 255, 255, 255),
            scale=2,
            font=FONT_5X7_ROUNDED,
        )

    _draw_micro_text(
        pixels,
        canvas_width,
        canvas_height,
        footer_x,
        footer_y,
        footer_text,
        (150, 160, 170, 120),
    )

    return bytes(pixels)


def render_weather_draw_png(
    codes: list[str],
    profile: str,
    unique: bool,
    sprite_path: Path,
) -> bytes:
    sprite_width, sprite_height, sprite_pixels = _load_sprite_sheet(str(sprite_path))
    if sprite_width != SPRITE_WIDTH or sprite_height != SPRITE_HEIGHT * SPRITE_COUNT:
        raise ValueError("unexpected_sprite_dimensions")

    slot_count = len(codes)
    card_width = 118
    card_height = 160
    card_gap = 18
    outer_padding_x = 16
    outer_padding_y = 16
    panel_padding_x = 24
    panel_padding_y = 18
    canvas_width = outer_padding_x * 2 + panel_padding_x * 2 + slot_count * card_width + max(slot_count - 1, 0) * card_gap
    canvas_height = 218
    card_top = outer_padding_y + panel_padding_y - 6
    card_left_start = outer_padding_x + panel_padding_x

    pixels = bytearray(_base_canvas_for_slot_count(slot_count))
    for index, code in enumerate(codes):
        tile_index = SPRITE_INDEX.get(code)
        if tile_index is None:
            raise ValueError(f"unknown_weather_code:{code}")
        tile = _extract_sprite_tile(sprite_pixels, sprite_width, tile_index)
        card_left = card_left_start + index * (card_width + card_gap)
        tile_x = card_left + 2
        tile_y = card_top + 2
        _blit_rgba(pixels, canvas_width, canvas_height, tile, SPRITE_WIDTH, SPRITE_HEIGHT, tile_x, tile_y)

    return _encode_png_rgba(canvas_width, canvas_height, bytes(pixels))
