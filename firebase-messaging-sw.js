// Firebase Cloud Messaging Service Worker
// 백그라운드에서 푸시 알림을 수신하는 Service Worker

// Firebase SDK 임포트 (Service Worker용)
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

// Firebase 설정 - 실제 값으로 업데이트
const firebaseConfig = {
    apiKey: "AIzaSyDQbXGuTe_w_I6THqr5gb1WoSJVKmOroew",
    authDomain: "memory-garden-2351b.firebaseapp.com",
    projectId: "memory-garden",
    storageBucket: "memory-garden.appspot.com",
    messagingSenderId: "794948119049",
    appId: "1:794948119049:web:db05a99551abb2e98026d8"
};

// Firebase 초기화
firebase.initializeApp(firebaseConfig);

// Messaging 인스턴스
const messaging = firebase.messaging();

// 백그라운드 메시지 수신 핸들러
messaging.onBackgroundMessage((payload) => {
    console.log('[firebase-messaging-sw.js] Received background message:', payload);

    const notificationTitle = payload.notification?.title || 'Memory Garden 🌱';
    const notificationOptions = {
        body: payload.notification?.body || '새로운 메시지가 있습니다.',
        icon: '/static/icon-192.png',
        badge: '/static/badge-72.png',
        tag: 'memory-garden-notification',
        requireInteraction: false,
        vibrate: [200, 100, 200],
        data: {
            url: payload.data?.deep_link || 'kakaotalk://talk/chat/_ZeUTxl',
            time: new Date().toISOString()
        }
    };

    // 알림 표시
    return self.registration.showNotification(notificationTitle, notificationOptions);
});

// 알림 클릭 핸들러
self.addEventListener('notificationclick', (event) => {
    console.log('[firebase-messaging-sw.js] Notification clicked:', event);

    event.notification.close();

    const urlToOpen = event.notification.data?.url || 'kakaotalk://talk/chat/_ZeUTxl';

    // 카카오톡 채널 열기
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // 이미 열린 창이 있으면 포커스
                for (let i = 0; i < clientList.length; i++) {
                    const client = clientList[i];
                    if (client.url.includes('memorygarden') && 'focus' in client) {
                        return client.focus();
                    }
                }

                // 새 창 열기
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Service Worker 설치
self.addEventListener('install', (event) => {
    console.log('[firebase-messaging-sw.js] Service Worker installed');
    self.skipWaiting();
});

// Service Worker 활성화
self.addEventListener('activate', (event) => {
    console.log('[firebase-messaging-sw.js] Service Worker activated');
    event.waitUntil(clients.claim());
});
