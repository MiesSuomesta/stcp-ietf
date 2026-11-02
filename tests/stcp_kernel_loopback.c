/* Live AF_STCP loopback test; no kernel modifications required. */
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
#define PAYLOAD_SIZE 1024
#define REPLY_SIZE 257

static int port = 19533;
static int listener = -1;
static int server_result = 1;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
static int server_ready = 0;

static void fill(unsigned char *buf, size_t len, unsigned seed) {
    for (size_t i = 0; i < len; i++) buf[i] = (unsigned char)((i * 37 + seed) & 255);
}
static int send_all(int fd, const unsigned char *p, size_t len) {
    while (len) {
        ssize_t n = send(fd, p, len, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        p += n; len -= (size_t)n;
    }
    return 0;
}
static int recv_all(int fd, unsigned char *p, size_t len) {
    while (len) {
        ssize_t n = recv(fd, p, len, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        p += n; len -= (size_t)n;
    }
    return 0;
}
static struct sockaddr_in address(void) {
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons((uint16_t)port);
    inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    return a;
}
static void notify_server_ready(void) {
    pthread_mutex_lock(&lock);
    server_ready = 1;
    pthread_cond_signal(&cond);
    pthread_mutex_unlock(&lock);
}
static void *server_main(void *unused) {
    (void)unused;
    int peer = -1;
    unsigned char got[PAYLOAD_SIZE], expected[PAYLOAD_SIZE], reply[REPLY_SIZE];
    struct sockaddr_in a = address();
    listener = socket(AF_STCP, SOCK_STREAM, STCP_PROTO_TCP);
    if (listener < 0) { perror("server socket"); goto done; }
    if (bind(listener, (struct sockaddr *)&a, sizeof(a)) < 0) { perror("server bind"); goto done; }
    if (listen(listener, 16) < 0) { perror("server listen"); goto done; }
    notify_server_ready();
    peer = accept(listener, NULL, NULL);
    if (peer < 0) { perror("server accept"); goto done; }
    fill(expected, sizeof(expected), 11);
    if (recv_all(peer, got, sizeof(got)) < 0) { perror("server recv"); goto done; }
    if (memcmp(got, expected, sizeof(got))) { fprintf(stderr, "FAIL: server payload mismatch\n"); goto done; }
    fill(reply, sizeof(reply), 99);
    if (send_all(peer, reply, sizeof(reply)) < 0) { perror("server send"); goto done; }
    server_result = 0;
done:
    if (peer >= 0) close(peer);
    if (listener >= 0) close(listener);
    notify_server_ready();
    return NULL;
}
int main(int argc, char **argv) {
    if (argc > 2) { fprintf(stderr, "usage: %s [port]\n", argv[0]); return 2; }
    if (argc == 2) {
        char *end;
        long p = strtol(argv[1], &end, 10);
        if (*end || p < 1 || p > 65535) { fprintf(stderr, "invalid port\n"); return 2; }
        port = (int)p;
    }
    /* Safety net: external timeout(1) is also recommended by the runner. */
    signal(SIGPIPE, SIG_IGN);
    pthread_t server;
    if (pthread_create(&server, NULL, server_main, NULL)) { perror("pthread_create"); return 1; }
    pthread_mutex_lock(&lock);
    while (!server_ready) pthread_cond_wait(&cond, &lock);
    pthread_mutex_unlock(&lock);
    if (listener < 0) { pthread_join(server, NULL); return 1; }
    int client = socket(AF_STCP, SOCK_STREAM, STCP_PROTO_TCP);
    if (client < 0) { perror("client socket"); return 1; }
    struct sockaddr_in a = address();
    if (connect(client, (struct sockaddr *)&a, sizeof(a)) < 0) { perror("client connect"); return 1; }
    unsigned char payload[PAYLOAD_SIZE], got[REPLY_SIZE], expected[REPLY_SIZE];
    fill(payload, sizeof(payload), 11);
    fill(expected, sizeof(expected), 99);
    if (send_all(client, payload, sizeof(payload)) < 0) { perror("client send"); return 1; }
    if (recv_all(client, got, sizeof(got)) < 0) { perror("client recv"); return 1; }
    if (memcmp(got, expected, sizeof(got))) { fprintf(stderr, "FAIL: client payload mismatch\n"); return 1; }
    close(client);
    pthread_join(server, NULL);
    if (server_result) { fprintf(stderr, "FAIL: server side\n"); return 1; }
    printf("PASS: AF_STCP TCP loopback, client->server=%d bytes, server->client=%d bytes\n", PAYLOAD_SIZE, REPLY_SIZE);
    puts("LIMITATION: no wire capture, crypto known-answer comparison, or Zephyr interoperability.");
    return 0;
}
