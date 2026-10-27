import shutil
import subprocess

SYSCALL_NAMES: dict[int, str] = {
    0: "read", 1: "write", 2: "open", 3: "close", 4: "stat", 5: "fstat",
    6: "lstat", 7: "poll", 8: "lseek", 9: "mmap", 10: "mprotect",
    11: "munmap", 12: "brk", 13: "rt_sigaction", 14: "rt_sigprocmask",
    15: "rt_sigreturn", 16: "ioctl", 21: "access", 22: "pipe",
    32: "dup", 33: "dup2", 39: "getpid", 41: "socket", 42: "connect",
    43: "accept", 44: "sendto", 45: "recvfrom", 56: "clone", 57: "fork",
    58: "vfork", 59: "execve", 60: "exit", 61: "wait4", 62: "kill",
    72: "fcntl", 79: "getcwd", 80: "chdir", 82: "rename", 83: "mkdir",
    84: "rmdir", 87: "unlink", 88: "symlink", 89: "readlink", 90: "chmod",
    92: "chown", 101: "ptrace", 105: "setuid", 106: "setgid", 110: "getppid",
    157: "prctl", 161: "chroot", 257: "openat", 288: "accept4",
    317: "seccomp", 322: "execveat",
}

def get_bpftrace_map_code() -> str:

    header = """\
    // Mapping all syscalls both ways, based on https://github.com/iovisor/bpftrace/blob/2c7a7a598dbe1aa790db2dfe2db242aa69137d5b/tools/syscount.bt
    // Generates using bash:
    //   $ apt-get install auditd
    //   $ ausyscall --dump | awk 'NR > 1 { printf("\\t@sysname[%d] = \\"%s\\";\\n", $1, $2); }';
    // Reverse mapping
    //   $ ausyscall --dump | awk 'NR > 1 { printf("\\t@sysnum[\\"%s\\"] = %d;\\n", $2, $1); }';
    printf("REGISTERING SYSCALLS...\\n");
    """

    mapping_names: dict[int, str] = SYSCALL_NAMES

    if shutil.which("ausyscall"):
        try:
            cmd = "ausyscall --dump"
            raw_output = subprocess.check_output(cmd, shell=True, encoding="utf-8")
            tmp_map = {}

            for line in raw_output.strip().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[0].isdigit():
                    tmp_map[int(parts[0])] = parts[1]
            
            if tmp_map: 
                mapping_names = tmp_map
        except Exception:
            print("WARN: ausyscall output parsing failed.")
    
    lines = [header]
    
    for sys_num, sys_name in mapping_names.items():
        lines.append(f' @sysname[{sys_num}] = "{sys_name}";')
    lines.append("\n    // Reverse mapping")

    for sys_num, sys_name in mapping_names.items():
        lines.append(f' @sysnum["{sys_name}"] = {sys_num};')

    return "\n".join(lines)
