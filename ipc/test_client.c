#include "ipc_proto.h"
#include <stdio.h>

int main(void) {
    int fd = vale_ipc_client_connect(VALE_SOCK_PATH);
    if (fd < 0) { printf("connect failed (is vale-wm running?)\n"); return 1; }
    printf("connected, fd=%d\n", fd);
    return 0;
}
