#!/usr/bin/env python3
"""Instala/atualiza o cliente Ragna4th usando o manifesto oficial.

Usa apenas a biblioteca padrão do Python. Cada download é aceito somente
quando o tamanho e o SHA-256 coincidem com o manifesto publicado pelo servidor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


HOST = "patching.ragna4th.com"
BASE_URL = f"https://{HOST}/builds/ignis/current"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Ragna4thLauncher/1.1 Chrome/131.0.0.0 Safari/537.36"
)
CHUNK_SIZE = 1024 * 1024
SAFETY_MARGIN = 512 * 1024 * 1024


class InstallError(RuntimeError):
    pass


def human_size(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def request_bytes(url: str, timeout: int = 90) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != HOST:
            raise InstallError(f"redirecionamento inesperado para {response.geturl()}")
        if response.status != 200:
            raise InstallError(f"servidor respondeu HTTP {response.status}")
        return response.read()


def fetch_manifest() -> tuple[str, list[dict[str, Any]], list[str]]:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            check_raw = request_bytes(f"{BASE_URL}/check")
            check = json.loads(check_raw)
            version = str(check["version"])
            expected_digest = str(check["manifestDigest"]).lower()
            if len(expected_digest) != 64:
                raise InstallError("digest inválido na resposta /check")

            manifest_raw = request_bytes(f"{BASE_URL}/fileList")
            actual_digest = hashlib.sha256(manifest_raw).hexdigest()
            if actual_digest != expected_digest:
                raise InstallError(
                    "o manifesto mudou durante a consulta; tentando novamente"
                )

            manifest = json.loads(manifest_raw)
            files = manifest["files"]
            directories = manifest.get("directories", [])
            if not isinstance(files, list) or not isinstance(directories, list):
                raise InstallError("formato inesperado do manifesto")
            return version, files, directories
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, InstallError) as exc:
            last_error = exc
            if attempt < 3:
                print(f"Falha ao consultar o servidor (tentativa {attempt}/3): {exc}")
                time.sleep(attempt * 2)
    raise InstallError(f"não foi possível obter o manifesto oficial: {last_error}")


def safe_relative_path(raw_name: str) -> Path:
    if not isinstance(raw_name, str) or "\0" in raw_name:
        raise InstallError("nome de arquivo inválido no manifesto")
    normalized = raw_name.replace("\\", "/")
    while normalized.startswith("/"):
        normalized = normalized[1:]
    pure = PurePosixPath(normalized)
    if (
        not normalized
        or normalized in (".", "..")
        or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise InstallError(f"caminho inseguro no manifesto: {raw_name!r}")
    return Path(*pure.parts)


def safe_destination(root: Path, raw_name: str) -> Path:
    destination = root / safe_relative_path(raw_name)
    resolved = destination.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise InstallError(f"caminho escaparia da pasta do jogo: {raw_name!r}") from exc
    return destination


def validate_record(record: dict[str, Any]) -> tuple[str, str, int]:
    try:
        hash_name = str(record["hashName"]).lower()
        checksum = str(record["checksum"]).lower()
        size = int(record["bytes"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InstallError("registro de arquivo inválido no manifesto") from exc
    hexadecimal = set("0123456789abcdef")
    if len(hash_name) != 64 or any(ch not in hexadecimal for ch in hash_name):
        raise InstallError("hashName inválido no manifesto")
    if len(checksum) != 64 or any(ch not in hexadecimal for ch in checksum):
        raise InstallError("checksum inválido no manifesto")
    if size < 0:
        raise InstallError("tamanho negativo no manifesto")
    return hash_name, checksum, size


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_local_files(
    root: Path, files: list[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], Path, str, str, int]], int]:
    pending: list[tuple[dict[str, Any], Path, str, str, int]] = []
    complete_bytes = 0
    total = len(files)
    for index, record in enumerate(files, 1):
        raw_name = record.get("name")
        if not isinstance(raw_name, str):
            raise InstallError("arquivo sem nome válido no manifesto")
        destination = safe_destination(root, raw_name)
        hash_name, checksum, size = validate_record(record)
        print(
            f"\rVerificando arquivos locais: {index}/{total}",
            end="",
            flush=True,
        )
        valid = False
        if destination.is_file() and destination.stat().st_size == size:
            valid = sha256_file(destination) == checksum
        if valid:
            complete_bytes += size
        else:
            pending.append((record, destination, hash_name, checksum, size))
    print()
    return pending, complete_bytes


def download_one(
    destination: Path,
    hash_name: str,
    checksum: str,
    expected_size: int,
    index: int,
    total_files: int,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/static/{quote(hash_name, safe='')}"
    display_name = str(destination.name)
    last_error: Exception | None = None

    for attempt in range(1, 4):
        temp_path: Path | None = None
        try:
            req = Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
            )
            with urlopen(req, timeout=120) as response:
                final = urlparse(response.geturl())
                if final.scheme != "https" or final.hostname != HOST:
                    raise InstallError(
                        f"redirecionamento inesperado para {response.geturl()}"
                    )
                if response.status != 200:
                    raise InstallError(f"servidor respondeu HTTP {response.status}")
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) != expected_size:
                    raise InstallError(
                        f"tamanho informado pelo servidor é {declared}, "
                        f"mas o manifesto exige {expected_size}"
                    )

                digest = hashlib.sha256()
                downloaded = 0
                started = time.monotonic()
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination.name}.",
                    suffix=".ragna4th-download",
                    dir=destination.parent,
                    delete=False,
                ) as temp:
                    temp_path = Path(temp.name)
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        temp.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        elapsed = max(time.monotonic() - started, 0.001)
                        percent = (
                            100.0
                            if expected_size == 0
                            else downloaded * 100.0 / expected_size
                        )
                        speed = downloaded / elapsed
                        print(
                            f"\r[{index}/{total_files}] {display_name}: "
                            f"{percent:6.2f}% "
                            f"({human_size(downloaded)}/{human_size(expected_size)}) "
                            f"a {human_size(int(speed))}/s",
                            end="",
                            flush=True,
                        )

            print()
            if downloaded != expected_size:
                raise InstallError(
                    f"tamanho recebido {downloaded}; esperado {expected_size}"
                )
            actual_checksum = digest.hexdigest()
            if actual_checksum != checksum:
                raise InstallError(
                    f"SHA-256 recebido {actual_checksum}; esperado {checksum}"
                )
            if temp_path is None:
                raise InstallError("arquivo temporário não foi criado")
            os.replace(temp_path, destination)
            print(f"OK: {destination.name}")
            return
        except KeyboardInterrupt:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            print()
            raise
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, InstallError) as exc:
            last_error = exc
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            if attempt < 3:
                print(f"\nFalha em {display_name} (tentativa {attempt}/3): {exc}")
                time.sleep(attempt * 3)
    raise InstallError(f"falha definitiva ao baixar {display_name}: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Instala/atualiza o Ragna4th pelo manifesto oficial."
    )
    parser.add_argument(
        "pasta",
        nargs="?",
        default="~/Games/Ragna4th",
        help="pasta do jogo (padrão: ~/Games/Ragna4th)",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="somente verifica e mostra quanto falta baixar",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="inicia sem pedir confirmação",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Erro: execute como usuário normal, sem sudo.", file=sys.stderr)
        return 2

    root = Path(args.pasta).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    print("Consultando o servidor oficial do Ragna4th...")
    version, files, directories = fetch_manifest()
    print(f"Versão remota: {version}")
    print(f"Arquivos no manifesto: {len(files)}")

    for raw_directory in directories:
        if not isinstance(raw_directory, str):
            raise InstallError("diretório inválido no manifesto")
        directory = safe_destination(root, raw_directory)
        directory.mkdir(parents=True, exist_ok=True)

    pending, complete_bytes = inspect_local_files(root, files)
    total_bytes = sum(validate_record(record)[2] for record in files)
    pending_bytes = total_bytes - complete_bytes

    print(f"Pasta: {root}")
    print(f"Tamanho total do cliente: {human_size(total_bytes)}")
    print(f"Já verificado: {human_size(complete_bytes)}")
    print(f"Falta baixar: {human_size(pending_bytes)} em {len(pending)} arquivo(s)")

    if args.plan:
        return 0
    if not pending:
        print("\nTudo certo: o cliente já está completo e íntegro.")
        print(f"Executável: {root / 'ragna4th.exe'}")
        return 0

    free = shutil.disk_usage(root).free
    required = pending_bytes + SAFETY_MARGIN
    if free < required:
        raise InstallError(
            f"espaço insuficiente: há {human_size(free)} livres, "
            f"mas são necessários aproximadamente {human_size(required)}"
        )

    if not args.yes:
        if not sys.stdin.isatty():
            raise InstallError("use --yes para iniciar sem terminal interativo")
        answer = input("Iniciar o download agora? [s/N] ").strip().lower()
        if answer not in ("s", "sim"):
            print("Cancelado; nenhum download foi iniciado.")
            return 0

    total_pending = len(pending)
    for index, (_record, destination, hash_name, checksum, size) in enumerate(
        pending, 1
    ):
        download_one(
            destination,
            hash_name,
            checksum,
            size,
            index,
            total_pending,
        )

    print("\nInstalação concluída e todos os arquivos baixados foram verificados.")
    print(f"Executável do jogo: {root / 'ragna4th.exe'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrompido. Você pode executar novamente depois.", file=sys.stderr)
        raise SystemExit(130)
    except InstallError as exc:
        print(f"\nErro: {exc}", file=sys.stderr)
        raise SystemExit(1)
