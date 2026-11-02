/* AF_STCP live TCP payload boundary / immediate DATA test.
 * Independent test program; does not modify production kernel or SDK.
 * Run under a process timeout. Payload is sent immediately after connect().
 */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#ifndef AF_STCP
#define AF_STCP 45
#endif
#define STCP_PROTO_TCP 253
#define MAX_PAYLOAD (1024 * 1024)
static int port, listener = -1, server_result = 1, server_ready;
static size_t size_bytes;
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv = PTHREAD_COND_INITIALIZER;
static unsigned char pattern(size_t i, unsigned seed) { return (unsigned char)((i * 73u + seed) & 255u); }
static int send_exact(int fd, const unsigned char *p, size_t n) {
    while (n) {
        ssize_t r = send(fd, p, n, MSG_NOSIGNAL);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) return -1;
        p += r; n -= (size_t)r;
    }
    return 0;
}
static int recv_exact(int fd, unsigned char *p, size_t n) {
    while (n) {
        ssize_t r = recv(fd, p, n, 0);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) return -1;
        p += r; n -= (size_t)r;
    }
    return 0;
}
static struct sockaddr_in addr(void) {
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port);
    inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    return a;
}
static void ready(void) {
    pthread_mutex_lock(&mu); server_ready = 1; pthread_cond_broadcast(&cv); pthread_mutex_unlock(&mu);
}
static void *server(void *arg) {
    (void)arg;
    int peer = -1;
    unsigned char *got = NULL, *reply = NULL;
    struct sockaddr_in a = addr();
    listener = socket(AF_STCP, SOCK_STREAM, STCP_PROTO_TCP);
    if (listener < 0) { perror("server socket"); goto out; }
    if (bind(listener, (struct sockaddr *)&a, sizeof(a)) < 0) { perror("bind"); goto out; }
    if (listen(listener, 8) < 0) { perror("listen"); goto out; }
    ready();
    peer = accept(listener, NULL, NULL);
    if (peer < 0) { perror("accept"); goto out; }
    got = malloc(size_bytes); reply = malloc(size_bytes);
    if (!got || !reply) { perror("malloc"); goto out; }
    if (recv_exact(peer, got, size_bytes)) { perror("server recv"); goto out; }
    for (size_t i=0; i<size_bytes; i++)
        if (got[i] != pattern(i, 11)) { fprintf(stderr,"server mismatch offset=%zu\n",i); goto out; }
    for (size_t i=0; i<size_bytes; i++) reply[i] = pattern(i, 99);
    if (send_exact(peer, reply, size_bytes)) { perror("server send"); goto out; }
    server_result = 0;
out:
    free(got); free(reply);
    if (peer >= 0) close(peer);
    if (listener >= 0) close(listener);
    ready();
    return NULL;
}
int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr,"usage: %s PORT SIZE_BYTES\n",argv[0]); return 2; }
    char *end = NULL;
    long p = strtol(argv[1], &end, 10);
    if (!end || *end || p < 1024 || p > 65535) return 2;
    port = (int)p;
    end = NULL;
    unsigned long n = strtoul(argv[2], &end, 10);
    if (!end || *end || n < 1 || n > MAX_PAYLOAD) return 2;
    size_bytes = (size_t)n;
    signal(SIGPIPE, SIG_IGN);
    pthread_t tid;
    if (pthread_create(&tid, NULL, server, NULL)) return 1;
    pthread_mutex_lock(&mu);
    while (!server_ready) pthread_cond_wait(&cv, &mu);
    pthread_mutex_unlock(&mu);
    if (listener < 0) { pthread_join(tid, NULL); return 1; }
    int client = socket(AF_STCP, SOCK_STREAM, STCP_PROTO_TCP);
    if (client < 0) { perror("client socket"); return 1; }
    struct sockaddr_in a = addr();
    if (connect(client, (struct sockaddr *)&a, sizeof(a))) { perror("connect"); return 1; }
    unsigned char *payload = malloc(size_bytes), *got = malloc(size_bytes);
    if (!payload || !got) { perror("malloc"); return 1; }
    for (size_t i=0; i<size_bytes; i++) payload[i] = pattern(i, 11);
    /* No artificial sleep: test the earliest application send after connect. */
    if (send_exact(client, payload, size_bytes)) { perror("client send"); return 1; }
    if (recv_exact(client, got, size_bytes)) { perror("client recv"); return 1; }
    for (size_t i=0; i<size_bytes; i++)
        if (got[i] != pattern(i, 99)) { fprintf(stderr,"client mismatch offset=%zu\n",i); return 1; }
    free(payload); free(got);
    close(client);
    pthread_join(tid, NULL);
    if (server_result) { fprintf(stderr,"server failure\n"); return 1; }
    printf("PASS AF_STCP TCP immediate DATA and bidirectional integrity size=%zu\n",size_bytes);
    return 0;
}
