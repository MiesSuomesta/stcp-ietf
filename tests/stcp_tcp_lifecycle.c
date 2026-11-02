/* Linux AF_STCP lifecycle test: repeated connect, immediate data, graceful close.
 * Independent test code, no kernel modifications. Use external timeout.
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
static int port, count, ready, result=1, listener=-1;
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond=PTHREAD_COND_INITIALIZER;
static struct sockaddr_in addr(void) {
    struct sockaddr_in a={0}; a.sin_family=AF_INET;
    a.sin_port=htons((uint16_t)port); inet_pton(AF_INET,"127.0.0.1",&a.sin_addr);
    return a;
}
static void notify(void) {
    pthread_mutex_lock(&mutex); ready=1; pthread_cond_broadcast(&cond);
    pthread_mutex_unlock(&mutex);
}
static int send_exact(int fd,const unsigned char *buf,size_t n) {
    while(n) { ssize_t r=send(fd,buf,n,MSG_NOSIGNAL);
        if(r<0 && errno==EINTR)continue;
        if(r<=0)return -1;buf+=r;n-=(size_t)r; }
    return 0;
}
static int recv_exact(int fd,unsigned char *buf,size_t n) {
    while(n) { ssize_t r=recv(fd,buf,n,0);
        if(r<0 && errno==EINTR)continue;
        if(r<=0)return -1;buf+=r;n-=(size_t)r; }
    return 0;
}
static void *server(void *arg) {
    (void)arg;struct sockaddr_in a=addr();
    listener=socket(AF_STCP,SOCK_STREAM,STCP_PROTO_TCP);
    if(listener<0){perror("server socket");goto out;}
    if(bind(listener,(struct sockaddr*)&a,sizeof(a))){perror("bind");goto out;}
    if(listen(listener,16)){perror("listen");goto out;}
    notify();
    for(int i=0;i<count;i++) {
        int fd=accept(listener,NULL,NULL);
        if(fd<0){perror("accept");goto out;}
        unsigned char request[8],response[8];
        if(recv_exact(fd,request,sizeof(request))){perror("server recv");close(fd);goto out;}
        uint32_t id;memcpy(&id,request,4);
        if(ntohl(id)!=(uint32_t)i || request[4]!=0x53 || request[5]!=0x54 || request[6]!=0x43 || request[7]!=0x50){
            fprintf(stderr,"request mismatch iteration %d\n",i);close(fd);goto out;
        }
        memcpy(response,request,8);response[4]=0x50;
        if(send_exact(fd,response,sizeof(response))){perror("server send");close(fd);goto out;}
        close(fd);
    }
    result=0;
out:
    if(listener>=0)close(listener);
    notify();return NULL;
}
int main(int argc,char **argv){
    if(argc!=3){fprintf(stderr,"usage: %s PORT COUNT\n",argv[0]);return 2;}
    char *end;long p=strtol(argv[1],&end,10);
    if(*end||p<1024||p>65535)return 2;
    port=(int)p;long n=strtol(argv[2],&end,10);
    if(*end||n<1||n>10000)return 2;
    count=(int)n;signal(SIGPIPE,SIG_IGN);
    pthread_t tid;
    if(pthread_create(&tid,NULL,server,NULL))return 1;
    pthread_mutex_lock(&mutex);
    while(!ready)pthread_cond_wait(&cond,&mutex);
    pthread_mutex_unlock(&mutex);
    if(listener<0){pthread_join(tid,NULL);return 1;}
    for(int i=0;i<count;i++){
        int fd=socket(AF_STCP,SOCK_STREAM,STCP_PROTO_TCP);
        if(fd<0){perror("client socket");return 1;}
        struct sockaddr_in a=addr();
        if(connect(fd,(struct sockaddr*)&a,sizeof(a))){perror("connect");close(fd);return 1;}
        unsigned char request[8]={0},response[8];
        uint32_t id=htonl((uint32_t)i);memcpy(request,&id,4);
        memcpy(request+4,"STCP",4);
        if(send_exact(fd,request,sizeof(request))||recv_exact(fd,response,sizeof(response))){
            perror("client transfer");close(fd);return 1;
        }
        request[4]='P';
        if(memcmp(request,response,8)){fprintf(stderr,"response mismatch %d\n",i);close(fd);return 1;}
        close(fd);
    }
    pthread_join(tid,NULL);
    if(result)return 1;
    printf("PASS: %d sequential connections with fresh sockets, bidirectional data and close\n",count);
    puts("LIMITATION: no forced disconnect, peer EOF assertion, UDP, Zephyr or malformed-wire injection.");
    return 0;
}
