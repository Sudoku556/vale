#ifndef VALE_IPC_PROTO_H
#define VALE_IPC_PROTO_H

#define VALE_SOCK_PATH "/tmp/vale-wm.sock"

int vale_ipc_server_init(const char *path);
int vale_ipc_client_connect(const char *path);

#endif
