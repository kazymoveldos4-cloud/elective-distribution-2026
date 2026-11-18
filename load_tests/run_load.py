import csv
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

import matplotlib.pyplot as plt
import psutil

# Пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database.db")
DB_BACKUP_PATH = os.path.join(BASE_DIR, "database.db.backup")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
LOCUSTFILE = os.path.join(BASE_DIR, "load_tests", "locustfile.py")
PYTHON_EXE = sys.executable

SCENARIOS = [
    {"name": "Сценарий 1 (5 польз.)", "users": 5, "spawn_rate": 2, "duration": "1m", "duration_sec": 60},
    {"name": "Сценарий 2 (20 польз.)", "users": 20, "spawn_rate": 5, "duration": "2m", "duration_sec": 120},
    {"name": "Сценарий 3 (50 польз.)", "users": 50, "spawn_rate": 10, "duration": "3m", "duration_sec": 180},
    {"name": "Сценарий 4 (100 польз.)", "users": 100, "spawn_rate": 20, "duration": "3m", "duration_sec": 180},
]


def backup_database():
    """Создание резервной копии базы данных перед нагрузочным тестированием."""
    if os.path.exists(DB_PATH):
        print(f"[DB] Создание резервной копии базы данных: {DB_BACKUP_PATH}")
        shutil.copy2(DB_PATH, DB_BACKUP_PATH)


def restore_database():
    """Восстановление исходной базы данных после нагрузочного тестирования."""
    if os.path.exists(DB_BACKUP_PATH):
        print(f"[DB] Восстановление базы данных из резервной копии...")
        shutil.copy2(DB_BACKUP_PATH, DB_PATH)
        os.remove(DB_BACKUP_PATH)
        print("[DB] База данных успешно восстановлена к исходному состоянию.")


def wait_for_server(url="http://127.0.0.1:8000/", timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def monitor_resources(pid, stop_event, samples):
    try:
        proc = psutil.Process(pid)
        proc.cpu_percent(interval=None)
        while not stop_event.is_set():
            time.sleep(0.5)
            try:
                all_procs = [proc] + proc.children(recursive=True)
                total_cpu = sum(p.cpu_percent(interval=None) for p in all_procs)
                total_mem = sum(p.memory_info().rss for p in all_procs) / (1024 * 1024)
                samples["cpu"].append(total_cpu)
                samples["mem"].append(total_mem)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    except Exception as e:
        print(f"[Monitor] Ошибка мониторинга процесса: {e}")


def parse_locust_stats(csv_prefix):
    stats_file = f"{csv_prefix}_stats.csv"
    if not os.path.exists(stats_file):
        print(f"[Parser] Файл статистики не найден: {stats_file}")
        return None

    with open(stats_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name") == "Aggregated":
                req_count = int(row.get("Request Count", 0))
                fail_count = int(row.get("Failure Count", 0))
                avg_time = float(row.get("Average Response Time", 0.0))
                max_time = float(row.get("Max Response Time", 0.0))
                rps = float(row.get("Requests/s", 0.0))
                err_rate = (fail_count / req_count * 100.0) if req_count > 0 else 0.0
                return {
                    "requests": req_count,
                    "failures": fail_count,
                    "avg_response_time": avg_time,
                    "max_response_time": max_time,
                    "rps": rps,
                    "error_rate": err_rate,
                }
    return None


def generate_charts(results):
    print("[Charts] Построение графиков производительности...")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    labels = [f"{r['users']} польз." for r in results]
    avg_times = [r["avg_response_time"] for r in results]
    max_times = [r["max_response_time"] for r in results]
    rps_values = [r["rps"] for r in results]
    cpu_avgs = [r["avg_cpu"] for r in results]
    cpu_maxs = [r["max_cpu"] for r in results]
    mem_avgs = [r["avg_mem"] for r in results]

    # График 1: Время отклика и RPS
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Время отклика
    ax1.plot(labels, avg_times, marker="o", color="blue", label="Ср. время (мс)", linewidth=2)
    ax1.plot(labels, max_times, marker="s", color="red", linestyle="--", label="Макс. время (мс)", linewidth=2)
    ax1.set_title("Время отклика API по сценариям нагрузки", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Нагрузка (число пользователей)")
    ax1.set_ylabel("Время отклика (мс)")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend()

    # RPS (Пропускная способность)
    bars = ax2.bar(labels, rps_values, color="teal", alpha=0.85, width=0.5)
    ax2.set_title("Пропускная способность (RPS)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Нагрузка (число пользователей)")
    ax2.set_ylabel("Запросов в секунду (RPS)")
    ax2.grid(axis="y", linestyle=":", alpha=0.6)
    for bar in bars:
        h = bar.get_height()
        ax2.annotate(f"{h:.1f}", (bar.get_x() + bar.get_width() / 2, h),
                     textcoords="offset points", xytext=(0, 3), ha="center", fontsize=10)

    plt.tight_layout()
    chart1_path = os.path.join(RESULTS_DIR, "response_time_and_rps.png")
    plt.savefig(chart1_path, dpi=200)
    plt.close()
    print(f"[Charts] Сохранён график: {chart1_path}")

    # График 2: Утилизация CPU и RAM
    fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(14, 5))

    # CPU
    ax3.plot(labels, cpu_avgs, marker="o", color="darkorange", label="Ср. CPU (%)", linewidth=2)
    ax3.plot(labels, cpu_maxs, marker="^", color="firebrick", linestyle="--", label="Макс. CPU (%)", linewidth=2)
    ax3.set_title("Нагрузка на процессор (CPU)", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Нагрузка (число пользователей)")
    ax3.set_ylabel("CPU (%)")
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.legend()

    # RAM
    bars_mem = ax4.bar(labels, mem_avgs, color="purple", alpha=0.75, width=0.5)
    ax4.set_title("Использование оперативной памяти (RAM)", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Нагрузка (число пользователей)")
    ax4.set_ylabel("RAM RSS (МБ)")
    ax4.grid(axis="y", linestyle=":", alpha=0.6)
    for bar in bars_mem:
        h = bar.get_height()
        ax4.annotate(f"{h:.1f} МБ", (bar.get_x() + bar.get_width() / 2, h),
                     textcoords="offset points", xytext=(0, 3), ha="center", fontsize=10)

    plt.tight_layout()
    chart2_path = os.path.join(RESULTS_DIR, "resource_utilization.png")
    plt.savefig(chart2_path, dpi=200)
    plt.close()
    print(f"[Charts] Сохранён график: {chart2_path}")


def save_reports(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_file = os.path.join(RESULTS_DIR, "load_results.csv")
    md_file = os.path.join(RESULTS_DIR, "load_results.md")

    # Сохранение в CSV
    fieldnames = [
        "scenario", "users", "duration", "requests", "failures",
        "avg_response_time_ms", "max_response_time_ms", "rps",
        "error_percent", "avg_cpu_pct", "max_cpu_pct", "avg_ram_mb", "max_ram_mb"
    ]
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for r in results:
            writer.writerow([
                r["name"], r["users"], r["duration"], r["requests"], r["failures"],
                f"{r['avg_response_time']:.2f}", f"{r['max_response_time']:.2f}", f"{r['rps']:.2f}",
                f"{r['error_rate']:.2f}%", f"{r['avg_cpu']:.1f}%", f"{r['max_cpu']:.1f}%",
                f"{r['avg_mem']:.1f}", f"{r['max_mem']:.1f}"
            ])
    print(f"[Report] CSV сохранён: {csv_file}")

    # Сохранение в Markdown
    md_content = """# Результаты нагрузочного тестирования «АРМ Замдекана»

Тестирование проводилось с помощью фреймворка **Locust** в 4 последовательных сценариях с параллельным замером метрик CPU и RAM серверного процесса FastAPI (Uvicorn).

| Сценарий | Пользователи | Длительность | Число запросов | Ср. время (мс) | Макс. время (мс) | RPS | Ошибки (%) | CPU ср. (%) | CPU макс. (%) | RAM ср. (МБ) | RAM макс. (МБ) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for r in results:
        md_content += (
            f"| **{r['name']}** | {r['users']} | {r['duration']} | {r['requests']} | "
            f"{r['avg_response_time']:.2f} | {r['max_response_time']:.2f} | {r['rps']:.1f} | "
            f"{r['error_rate']:.2f}% | {r['avg_cpu']:.1f}% | {r['max_cpu']:.1f}% | "
            f"{r['avg_mem']:.1f} | {r['max_mem']:.1f} |\n"
        )

    md_content += """
---
## Графики производительности:
- **Время отклика и RPS:** `results/response_time_and_rps.png`
- **Утилизация CPU и RAM:** `results/resource_utilization.png`
"""

    with open(md_file, mode="w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[Report] Markdown сохранён: {md_file}")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    backup_database()

    print("[Backend] Запуск Uvicorn сервера (без --reload)...")
    server_cmd = [
        PYTHON_EXE, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]
    log_path = os.path.join(RESULTS_DIR, "uvicorn_server.log")
    server_log = open(log_path, "w", encoding="utf-8")
    server_proc = subprocess.Popen(server_cmd, stdout=server_log, stderr=server_log)

    try:
        if not wait_for_server():
            print("[ERROR] Не удалось подключиться к серверу за 45 секунд")
            server_log.flush()
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    print(f"[Backend Log]:\n{f.read()}")
            sys.exit(1)
        print(f"[Backend] Сервер готов к нагрузочному тестированию (PID {server_proc.pid}).")

        results = []

        for idx, sc in enumerate(SCENARIOS, 1):
            print(f"\n========================================================")
            print(f"Запуск: {sc['name']} (Пользователи: {sc['users']}, Длительность: {sc['duration']})")
            print(f"========================================================")

            csv_prefix = os.path.join(RESULTS_DIR, f"locust_scen_{idx}")

            # Запуск фонового мониторинга ресурсов
            stop_event = threading.Event()
            samples = {"cpu": [], "mem": []}
            monitor_thread = threading.Thread(
                target=monitor_resources,
                args=(server_proc.pid, stop_event, samples),
                daemon=True,
            )
            monitor_thread.start()

            locust_cmd = [
                PYTHON_EXE, "-m", "locust",
                "-f", LOCUSTFILE,
                "--headless",
                "-u", str(sc["users"]),
                "-r", str(sc["spawn_rate"]),
                "-t", sc["duration"],
                "--host", "http://127.0.0.1:8000",
                "--csv", csv_prefix,
                "--only-summary",
            ]

            start_t = time.time()
            loc_proc = subprocess.run(locust_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elapsed = time.time() - start_t

            stop_event.set()
            monitor_thread.join(timeout=2)

            stats = parse_locust_stats(csv_prefix)
            if not stats:
                print(f"[WARN] Не удалось разобрать статистику для {sc['name']}. Вывод Locust:")
                print(loc_proc.stdout)
                print(loc_proc.stderr)
                stats = {
                    "requests": 0, "failures": 0, "avg_response_time": 0.0,
                    "max_response_time": 0.0, "rps": 0.0, "error_rate": 0.0
                }

            cpu_samples = samples["cpu"] or [0.0]
            mem_samples = samples["mem"] or [0.0]

            scenario_res = {
                "name": sc["name"],
                "users": sc["users"],
                "duration": sc["duration"],
                "requests": stats["requests"],
                "failures": stats["failures"],
                "avg_response_time": stats["avg_response_time"],
                "max_response_time": stats["max_response_time"],
                "rps": stats["rps"],
                "error_rate": stats["error_rate"],
                "avg_cpu": sum(cpu_samples) / len(cpu_samples),
                "max_cpu": max(cpu_samples),
                "avg_mem": sum(mem_samples) / len(mem_samples),
                "max_mem": max(mem_samples),
            }
            results.append(scenario_res)

            print(f"[Done] Запросов: {scenario_res['requests']}, RPS: {scenario_res['rps']:.1f}, "
                  f"Ср. время: {scenario_res['avg_response_time']:.1f} мс, Ошибок: {scenario_res['error_rate']:.2f}%, "
                  f"CPU: {scenario_res['avg_cpu']:.1f}%, RAM: {scenario_res['avg_mem']:.1f} МБ")

            time.sleep(2)  # Небольшая пауза между сценариями

        # Построение графиков и отчетов
        generate_charts(results)
        save_reports(results)

        print("\n=== Все 4 сценария успешно завершены! ===")

    finally:
        print("[Backend] Остановка сервера...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        server_log.close()
        print("[Backend] Сервер остановлен.")
        restore_database()


if __name__ == "__main__":
    main()
