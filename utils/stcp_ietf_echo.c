/* SPDX-License-Identifier: MIT
 * Linux AF_STCP echo test utility for STCP IETF interoperability testing.
 * Build: cc -O2 -Wall -Wextra -pthread -o stcp_ietf_echo stcp_ietf_echo.c
 * Run:   ./stcp_ietf_echo [bind-ipv4] [port]
 * Example: ./stcp_ietf_echo 192.168.1.242 19000
 *
 * Uses real AF_STCP sockets, not AF_INET TCP sockets. The IPv4 sockaddr_in
 * is the address format supported by the Linux AF_STCP implementation.
 * Each accepted client gets a detached thread, so a stalled recv() cannot
 * prevent the server from accepting another client.
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
#define IPPROTO_STCP_TCP 253
#define DEFAULT_PORT 19000
#define BUFFER_SIZE 4096

struct client_arg { int fd; unsigned long id; };
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned long next_client_id = 0;

static void *handle_client(void *arg) {
    struct client_arg *client = arg;
    int fd = client->fd;
    unsigned long id = client->id;
    free(client);
    unsigned char buffer[BUFFER_SIZE];
    unsigned long long total = 0;
    int failed = 0;

    pthread_mutex_lock(&log_lock);
    printf("client %lu: accepted\n", id);
    fflush(stdout);
    pthread_mutex_unlock(&log_lock);

    for (;;) {
        ssize_t n = recv(fd, buffer, sizeof(buffer), 0);
        if (n == 0) break;
        if (n < 0) {
            if (errno == EINTR) continue;
            pthread_mutex_lock(&log_lock);
            fprintf(stderr, "client %lu: recv failed: %s\n", id, strerror(errno));
            pthread_mutex_unlock(&log_lock);
            failed = 1;
            break;
        }
        size_t sent = 0;
        while (sent < (size_t)n) {
            ssize_t w = send(fd, buffer + sent, (size_t)n - sent, MSG_NOSIGNAL);
            if (w < 0 && errno == EINTR) continue;
            if (w <= 0) {
                pthread_mutex_lock(&log_lock);
                fprintf(stderr, "client %lu: send failed: %s\n", id,
                        w < 0 ? strerror(errno) : "zero-byte send");
                pthread_mutex_unlock(&log_lock);
                failed = 1;
                break;
            }
            sent += (size_t)w;
        }
        if (failed) break;
        total += (unsigned long long)n;
        pthread_mutex_lock(&log_lock);
        printf("client %lu: echoed %zd bytes (total %llu)\n", id, n, total);
        fflush(stdout);
        pthread_mutex_unlock(&log_lock);
    }
    close(fd);
    pthread_mutex_lock(&log_lock);
    printf("client %lu: closed (%s; echoed %llu bytes)\n", id,
           failed ? "error" : "EOF", total);
    fflush(stdout);
    pthread_mutex_unlock(&log_lock);
    return NULL;
}

int main(int argc, char **argv) {
    const char *bind_ip = argc > 1 ? argv[1] : "0.0.0.0";
    unsigned long port = DEFAULT_PORT;
    if (argc > 3) {
        fprintf(stderr, "usage: %s [bind-ipv4] [port]\n", argv[0]);
        return EXIT_FAILURE;
    }
    if (argc == 3) {
        char *end = NULL;
        errno = 0;
        port = strtoul(argv[2], &end, 10);
        if (errno || end == argv[2] || *end || port == 0 || port > 65535) {
            fprintf(stderr, "invalid port: %s\n", argv[2]);
            return EXIT_FAILURE;
        }
    }
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, bind_ip, &addr.sin_addr) != 1) {
        fprintf(stderr, "invalid IPv4 address: %s\n", bind_ip);
        return EXIT_FAILURE;
    }
    signal(SIGPIPE, SIG_IGN);
    int listener = socket(AF_STCP, SOCK_STREAM, IPPROTO_STCP_TCP);
    if (listener < 0) { perror("AF_STCP socket"); return EXIT_FAILURE; }
    if (bind(listener, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("AF_STCP bind"); close(listener); return EXIT_FAILURE;
    }
    if (listen(listener, 16) < 0) {
        perror("AF_STCP listen"); close(listener); return EXIT_FAILURE;
    }
    printf("STCP echo listening on %s:%lu (AF_STCP=%d, protocol=%d)\n",
           bind_ip, port, AF_STCP, IPPROTO_STCP_TCP);
    fflush(stdout);

    for (;;) {
        int fd = accept(listener, NULL, NULL);
        if (fd < 0) {
            if (errno == EINTR) continue;
            fprintf(stderr, "AF_STCP accept failed: %s\n", strerror(errno));
            continue;
        }
        struct client_arg *client = malloc(sizeof(*client));
        if (!client) { perror("malloc"); close(fd); continue; }
        client->fd = fd;
        client->id = ++next_client_id;
        pthread_t thread;
        int rc = pthread_create(&thread, NULL, handle_client, client);
        if (rc != 0) {
            fprintf(stderr, "pthread_create failed: %s\n", strerror(rc));
            close(fd);
            free(client);
            continue;
        }
        pthread_detach(thread);
    }
    close(listener);
    return EXIT_SUCCESS;
}
