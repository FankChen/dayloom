package app.dayloom.personal;

import android.app.Notification;
import android.content.Context;
import android.content.SharedPreferences;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import java.util.Collections;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import org.json.JSONArray;
import org.json.JSONObject;

public class DayloomNotificationListener extends NotificationListenerService {
    static volatile DayloomNotificationListener current;
    private static final Pattern SENSITIVE = Pattern.compile("(?i)(otp|verification|passcode|password|one.time|\\b[0-9]{4,8}\\b|\u9a8c\u8bc1\u7801|\u5bc6\u7801)");
    private final ThreadPoolExecutor writer = new ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(64), new ThreadPoolExecutor.DiscardOldestPolicy());

    @Override
    public void onListenerConnected() { current = this; }

    @Override
    public void onListenerDisconnected() {
        current = null;
        synchronized (SecureVault.class) {
            getSharedPreferences("dayloom.notifications", MODE_PRIVATE).edit().putBoolean("enabled", false).commit();
            SecureVault.remove(this, "notification-events");
        }
    }

    @Override
    public void onNotificationPosted(StatusBarNotification notification) {
        if (writer.isShutdown()) return;
        writer.execute(() -> capture(notification));
    }

    private void capture(StatusBarNotification notification) {
        SharedPreferences preferences = getSharedPreferences("dayloom.notifications", MODE_PRIVATE);
        if (!preferences.getBoolean("enabled", false) || !preferences.getStringSet("packages", Collections.emptySet()).contains(notification.getPackageName())) return;
        Notification item = notification.getNotification();
        if (item.visibility == Notification.VISIBILITY_SECRET) return;
        String title = String.valueOf(item.extras.getCharSequence(Notification.EXTRA_TITLE, ""));
        String body = String.valueOf(item.extras.getCharSequence(Notification.EXTRA_BIG_TEXT, item.extras.getCharSequence(Notification.EXTRA_TEXT, "")));
        if (SENSITIVE.matcher(title + " " + body).find()) return;
        try {
            synchronized (SecureVault.class) {
                if (!preferences.getBoolean("enabled", false) || !preferences.getStringSet("packages", Collections.emptySet()).contains(notification.getPackageName())) return;
                JSONArray previous = retained(this, notification.getKey());
                JSONArray next = new JSONArray();
                JSONObject entry = new JSONObject();
                entry.put("id", UUID.randomUUID().toString());
                entry.put("key", notification.getKey());
                entry.put("packageName", notification.getPackageName());
                entry.put("title", title.substring(0, Math.min(200, title.length())));
                entry.put("body", body.substring(0, Math.min(4000, body.length())));
                entry.put("capturedAt", System.currentTimeMillis());
                next.put(entry);
                for (int index = 0; index < previous.length() && index < 99; index++) next.put(previous.get(index));
                SecureVault.put(this, "notification-events", next.toString());
            }
        } catch (Exception failure) {
            SecureVault.remove(this, "notification-events");
        }
    }

    static JSONArray retained(Context context, String excludeKey) throws Exception {
        String value = SecureVault.get(context, "notification-events");
        JSONArray original = new JSONArray(value == null ? "[]" : value);
        JSONArray retained = new JSONArray();
        long minimum = System.currentTimeMillis() - 86400000L;
        for (int index = 0; index < original.length(); index++) {
            JSONObject item = original.getJSONObject(index);
            if (item.optLong("capturedAt") > minimum && !item.optString("key").equals(excludeKey)) retained.put(item);
        }
        return retained;
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification notification) {
        if (writer.isShutdown()) return;
        writer.execute(() -> {
            try {
                synchronized (SecureVault.class) {
                    SecureVault.put(this, "notification-events", retained(this, notification.getKey()).toString());
                }
            } catch (Exception failure) { SecureVault.remove(this, "notification-events"); }
        });
    }

    @Override
    public void onDestroy() {
        current = null;
        writer.shutdownNow();
        super.onDestroy();
    }
}