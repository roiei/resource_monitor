import time
import psutil
import curses
import subprocess
import re
import sys
import time
from datetime import datetime
from options import *


def bytes_to_gb(bytes):
    return bytes / (1024**3)


def mb_to_gb(mb):
    return mb / (1024)


def get_gpu_memory_info():
    cmd = ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits']
    output = subprocess.check_output(cmd).decode('utf-8')
    gpu_info = [tuple(map(int, line.split(', '))) for line in output.strip().split('\n')]
    return gpu_info


def write_row(stdscr, row_idx, col_idx, content, file, file_write_interval, loop):
    stdscr.addstr(row_idx, col_idx, content)
    if file and loop % file_write_interval == 0:
        file.write(content + "\n")


def mem_check(stdscr):
    first_cpu_usage = psutil.cpu_percent()

    curses.curs_set(0)  # hide cursor
    stdscr.nodelay(1)   # not to block getch()

    proc = subprocess.Popen(['nvidia-smi', '--loop-ms=1000', '--format=csv,noheader,nounits',
                         '--query-gpu=memory.used,memory.total'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    mem = psutil.virtual_memory()
    first_used_memory_gb = bytes_to_gb(mem.used)

    process = psutil.Process()
    with process.oneshot():
        mem_info = process.memory_full_info()
        first_rss_gb = bytes_to_gb(mem_info.rss)
        first_uss_gb = bytes_to_gb(mem_info.uss)
    
    file = None
    file_write_interval = 10
    loop = 0
    if 'out_file' in opts:
        file = open(opts['out_file'], 'w')
    
    start_time = time.time()

    try:
        while True:
            mem = psutil.virtual_memory()
            total_memory_gb = bytes_to_gb(mem.total)
            used_memory_gb = bytes_to_gb(mem.used)
            used_memory_percent = mem.percent

            process = psutil.Process()
            with process.oneshot():
                mem_info = process.memory_full_info()
                rss_gb = bytes_to_gb(mem_info.rss)
                uss_gb = bytes_to_gb(mem_info.uss)

            inc_tot_mem_gb = used_memory_gb - first_used_memory_gb
            inc_ratio = inc_tot_mem_gb / total_memory_gb * 100

            stdscr.clear()
            write_row(stdscr, 0, 0, "|  type | total (GB) | used (GB) |   used (%) | 1st used |      inc |  inc % |", file, file_write_interval, loop)
            write_row(stdscr, 1, 0, "|-------|------------|-----------|------------|----------|----------|--------|", file, file_write_interval, loop)
            write_row(stdscr, 2, 0, f"|  Page | {total_memory_gb:10.3f} | {used_memory_gb:9.3f} | {used_memory_percent:8.2f} % | {first_used_memory_gb:8.2f} | {inc_tot_mem_gb:8.2f} | {inc_ratio:6.2f} |", file, file_write_interval, loop)
            write_row(stdscr, 3, 0, f"|   RSS | {'-':>10} | {rss_gb:9.3f} | {'-':>10} | {first_rss_gb:8.2f} | {'-':>8} | {'-':>6} |", file, file_write_interval, loop)
            write_row(stdscr, 4, 0, f"|   SHD | {'-':>10} | {rss_gb:9.3f} | {'-':>10} | {first_rss_gb:8.2f} | {'-':>8} | {'-':>6} |", file, file_write_interval, loop)
            write_row(stdscr, 5, 0, f"|   USS | {'-':>10} | {uss_gb:9.3f} | {'-':>10} | {first_uss_gb:8.2f} | {'-':>8} | {'-':>6} |", file, file_write_interval, loop)

            row_idx = 5
            for idx, (used, total) in enumerate(get_gpu_memory_info()):
                used_mb = mb_to_gb(used)
                total_mb = mb_to_gb(total)
                used_percent = (used / total) * 100
                write_row(stdscr, row_idx, 0, f"| GPU {idx} | {total_mb:10.3f} | {used_mb:9.3f} | {used_percent:8.2f} % | {'-':>8} | {'-':>8} | {'-':>6} |", file, file_write_interval, loop)
                row_idx += 1
            
            cpu_usage = psutil.cpu_percent()
            upc_inc_usage = cpu_usage - first_cpu_usage

            write_row(stdscr, row_idx, 0, f"|   CPU | {'N/A':>10} | {'N/A':>9} | {cpu_usage:8.2f} % | {'-':>8} | {upc_inc_usage:>8.2f} | {'-':>6} |", file, file_write_interval, loop)
            row_idx += 1

            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

            elapsed_time = time.time() - start_time

            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)

            write_row(stdscr, row_idx + 1, 0, f"current time = {formatted_time}", file, file_write_interval, loop)
            row_idx += 1
            write_row(stdscr, row_idx + 1, 0, f"elapsed time = {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d} sec", file, file_write_interval, loop)
            row_idx += 1

            stdscr.refresh()

            k = stdscr.getch()
            if k == ord('q'):
                break

            time.sleep(1)
            loop += 1
    finally:
        proc.terminate()
        if file:
            file.close()


opts = get_opts(sys.argv)

curses.wrapper(mem_check)
