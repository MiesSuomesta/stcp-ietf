/* Experimental AF_STCP protocol 254 UDP live smoke test.
 * Explicitly probes whether UDP server supports bind/listen/accept.
 * No kernel or SDK modifications. Use with an external timeout.
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
#define STCP_PROTO_UDP 254
static int port=19700,ready=0,listener=-1,result=1;
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv=PTHREAD_COND_INITIALIZER;
static struct sockaddr_in address(void){
    struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons((uint16_t)port);
    inet_pton(AF_INET,"127.0.0.1",&a.sin_addr);return a;
}
static void signal_ready(void){pthread_mutex_lock(&mu);ready=1;pthread_cond_broadcast(&cv);pthread_mutex_unlock(&mu);}
static void *server(void *unused){
    (void)unused;int peer=-1;struct sockaddr_in a=address();
    listener=socket(AF_STCP,SOCK_DGRAM,STCP_PROTO_UDP);
    if(listener<0){perror("UDP server socket");goto done;}
    if(bind(listener,(struct sockaddr*)&a,sizeof(a))){perror("UDP server bind");goto done;}
    if(listen(listener,8)){perror("UDP server listen");goto done;}
    signal_ready();
    peer=accept(listener,NULL,NULL);
    if(peer<0){perror("UDP server accept");goto done;}
    unsigned char got[32],expected[32];
    for(int i=0;i<32;i++)expected[i]=(unsigned char)(i*17+3);
    ssize_t n=recv(peer,got,sizeof(got),0);
    if(n!=32||memcmp(got,expected,32)){fprintf(stderr,"UDP server payload mismatch or recv error: n=%zd errno=%d\n",n,errno);goto done;}
    n=send(peer,got,32,MSG_NOSIGNAL);
    if(n!=32){perror("UDP server reply");goto done;}
    result=0;
done:
    if(peer>=0)close(peer);if(listener>=0)close(listener);signal_ready();return NULL;
}
int main(int argc,char**argv){
    if(argc>2){fprintf(stderr,"usage: %s [PORT]\n",argv[0]);return 2;}
    if(argc==2){char *end;long p=strtol(argv[1],&end,10);if(*end||p<1024||p>65535)return 2;port=(int)p;}
    signal(SIGPIPE,SIG_IGN);pthread_t t;if(pthread_create(&t,NULL,server,NULL))return 1;
    pthread_mutex_lock(&mu);while(!ready)pthread_cond_wait(&cv,&mu);pthread_mutex_unlock(&mu);
    if(listener<0){pthread_join(t,NULL);return 1;}
    int fd=socket(AF_STCP,SOCK_DGRAM,STCP_PROTO_UDP);
    if(fd<0){perror("UDP client socket");return 1;}
    struct sockaddr_in a=address();
    if(connect(fd,(struct sockaddr*)&a,sizeof(a))){perror("UDP client connect");close(fd);return 1;}
    unsigned char payload[32],got[32];
    for(int i=0;i<32;i++)payload[i]=(unsigned char)(i*17+3);
    ssize_t n=send(fd,payload,32,MSG_NOSIGNAL);
    if(n!=32){perror("UDP client send");close(fd);return 1;}
    n=recv(fd,got,32,0);
    if(n!=32||memcmp(got,payload,32)){fprintf(stderr,"UDP client reply mismatch or recv error: n=%zd errno=%d\n",n,errno);close(fd);return 1;}
    close(fd);pthread_join(t,NULL);
    if(result)return 1;
    puts("PASS AF_STCP UDP loopback, 32-byte datagram each direction");
    return 0;
}
