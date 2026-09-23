#include "ipc_proto.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <string.h>

int vale_ipc_server_init(const char *path) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un addr = {0};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    unlink(path);
    bind(fd, (struct sockaddr *)&addr, sizeof(addr));
    listen(fd, 8);
    return fd;
}

int vale_ipc_client_connect(const char *path) {
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un addr = {0};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    connect(fd, (struct sockaddr *)&addr, sizeof(addr));
    return fd;
}
