/* AF_STCP protocol 254 live UDP message-boundary test.
 * One connected client per test run; one message at a time, exact recv length.
 * Independent test code. External timeout mandatory.
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
#define PROTO 254
#define MAX_LEN 65536
static int port, nmsgs, server_ok, ready, listener=-1;
static size_t *sizes;
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv=PTHREAD_COND_INITIALIZER;
static struct sockaddr_in address(void){struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons((uint16_t)port);inet_pton(AF_INET,"127.0.0.1",&a.sin_addr);return a;}
static void wake(void){pthread_mutex_lock(&mu);ready=1;pthread_cond_broadcast(&cv);pthread_mutex_unlock(&mu);}
static unsigned char pattern(int msg,size_t i){return (unsigned char)((msg*37u+i*73u+11u)&255u);}
static int check(const unsigned char *b,int msg,size_t n){for(size_t i=0;i<n;i++)if(b[i]!=pattern(msg,i)){fprintf(stderr,"mismatch msg=%d offset=%zu\n",msg,i);return -1;}return 0;}
static void *server(void *unused){
 (void)unused;int fd=-1;unsigned char *buf=malloc(MAX_LEN);struct sockaddr_in a=address();
 if(!buf){perror("malloc");goto done;}
 listener=socket(AF_STCP,SOCK_DGRAM,PROTO);
 if(listener<0){perror("server socket");goto done;}
 if(bind(listener,(struct sockaddr*)&a,sizeof(a))){perror("bind");goto done;}
 if(listen(listener,8)){perror("listen");goto done;}
 wake();fd=accept(listener,NULL,NULL);if(fd<0){perror("accept");goto done;}
 for(int m=0;m<nmsgs;m++){
   ssize_t r=recv(fd,buf,MAX_LEN,0);
   if(r!=(ssize_t)sizes[m]){fprintf(stderr,"server message length %d expected %zu got %zd errno %d\n",m,sizes[m],r,errno);goto done;}
   if(check(buf,m,sizes[m]))goto done;
   r=send(fd,buf,sizes[m],MSG_NOSIGNAL);
   if(r!=(ssize_t)sizes[m]){fprintf(stderr,"server reply %d expected %zu got %zd errno %d\n",m,sizes[m],r,errno);goto done;}
 }
 server_ok=1;
done:
 if(fd>=0)close(fd);if(listener>=0)close(listener);free(buf);wake();return NULL;
}
int main(int argc,char**argv){
 if(argc<3){fprintf(stderr,"usage: %s PORT SIZE [SIZE ...]\n",argv[0]);return 2;}
 char *end;long p=strtol(argv[1],&end,10);if(*end||p<1024||p>65535)return 2;port=(int)p;
 nmsgs=argc-2;sizes=calloc((size_t)nmsgs,sizeof(*sizes));if(!sizes)return 1;
 for(int m=0;m<nmsgs;m++){unsigned long n=strtoul(argv[m+2],&end,10);if(*end||n<1||n>MAX_LEN)return 2;sizes[m]=(size_t)n;}
 signal(SIGPIPE,SIG_IGN);pthread_t tid;if(pthread_create(&tid,NULL,server,NULL))return 1;
 pthread_mutex_lock(&mu);while(!ready)pthread_cond_wait(&cv,&mu);pthread_mutex_unlock(&mu);
 if(listener<0){pthread_join(tid,NULL);return 1;}
 int fd=socket(AF_STCP,SOCK_DGRAM,PROTO);if(fd<0){perror("client socket");return 1;}
 struct sockaddr_in a=address();if(connect(fd,(struct sockaddr*)&a,sizeof(a))){perror("connect");return 1;}
 unsigned char *tx=malloc(MAX_LEN),*rx=malloc(MAX_LEN);if(!tx||!rx)return 1;
 for(int m=0;m<nmsgs;m++){
   for(size_t i=0;i<sizes[m];i++)tx[i]=pattern(m,i);
   ssize_t r=send(fd,tx,sizes[m],MSG_NOSIGNAL);
   if(r!=(ssize_t)sizes[m]){fprintf(stderr,"client send %d expected %zu got %zd errno %d\n",m,sizes[m],r,errno);return 1;}
   r=recv(fd,rx,MAX_LEN,0);
   if(r!=(ssize_t)sizes[m]){fprintf(stderr,"client recv %d expected %zu got %zd errno %d\n",m,sizes[m],r,errno);return 1;}
   if(check(rx,m,sizes[m]))return 1;
 }
 close(fd);pthread_join(tid,NULL);free(tx);free(rx);free(sizes);
 if(!server_ok)return 1;
 printf("PASS AF_STCP UDP message boundaries and integrity messages=%d\n",nmsgs);return 0;
}
