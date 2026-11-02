package app.dayloom.personal;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.provider.Settings;
import android.service.notification.StatusBarNotification;
import androidx.core.app.NotificationManagerCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import org.json.JSONObject;

@CapacitorPlugin(name = "DayloomNative")
public class DayloomNativePlugin extends Plugin {
    private boolean validKey(String key) { return Arrays.asList("auth-session", "login-verifier").contains(key); }

    @PluginMethod
    public void getSecret(PluginCall call) {
        String key = call.getString("key");
        if (!validKey(key)) { call.reject("Unsupported secret key"); return; }
        try {
            String value = SecureVault.get(getContext(), key);
            JSObject response = new JSObject();
            response.put("value", value == null ? JSONObject.NULL : value);
            call.resolve(response);
        } catch (Exception failure) { call.reject("Secure storage is unavailable"); }
    }

    @PluginMethod
    public void setSecret(PluginCall call) {
        String key = call.getString("key");
        String value = call.getString("value");
        if (!validKey(key) || value == null || value.length() > 16000) { call.reject("Invalid secret input"); return; }
        try { SecureVault.put(getContext(), key, value); call.resolve(); }
        catch (Exception failure) { call.reject("Secure storage write failed"); }
    }

    @PluginMethod
    public void removeSecret(PluginCall call) {
        String key = call.getString("key");
        if (!validKey(key)) { call.reject("Unsupported secret key"); return; }
        SecureVault.remove(getContext(), key);
        call.resolve();
    }

    private boolean granted() {
        return NotificationManagerCompat.getEnabledListenerPackages(getContext()).contains(getContext().getPackageName());
    }

    @PluginMethod
    public void notificationStatus(PluginCall call) {
        SharedPreferences preferences = getContext().getSharedPreferences("dayloom.notifications", Context.MODE_PRIVATE);
        boolean permission = granted();
        if (!permission) {
            synchronized (SecureVault.class) {
                preferences.edit().putBoolean("enabled", false).commit();
                SecureVault.remove(getContext(), "notification-events");
            }
        }
        JSObject response = new JSObject();
        response.put("supported", true);
        response.put("granted", permission);
        response.put("enabled", permission && preferences.getBoolean("enabled", false));
        response.put("packages", new JSArray(preferences.getStringSet("packages", Collections.emptySet()).toArray()));
        call.resolve(response);
    }

    @PluginMethod
    public void openNotificationAccess(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            getActivity().startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
            call.resolve();
        });
    }

    @PluginMethod
    public void notificationSources(PluginCall call) {
        JSArray sources = new JSArray();
        DayloomNotificationListener listener = DayloomNotificationListener.current;
        if (granted() && listener != null) {
            Set<String> seen = new HashSet<>();
            for (StatusBarNotification notification : listener.getActiveNotifications()) {
                String name = notification.getPackageName();
                if (seen.add(name) && !name.equals(getContext().getPackageName())) {
                    JSObject source = new JSObject();
                    source.put("packageName", name);
                    sources.put(source);
                }
            }
        }
        JSObject response = new JSObject();
        response.put("sources", sources);
        call.resolve(response);
    }

    @PluginMethod
    public void configureNotifications(PluginCall call) {
        boolean enabled = Boolean.TRUE.equals(call.getBoolean("enabled", false));
        if (enabled && !granted()) { call.reject("Notification access is not granted"); return; }
        try {
            JSArray packages = call.getArray("packages", new JSArray());
            if (packages.length() > 50) { call.reject("Too many notification sources"); return; }
            Set<String> selected = new HashSet<>();
            for (int index = 0; index < packages.length(); index++) {
                String name = packages.getString(index);
                if (!name.matches("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+")) { call.reject("Invalid package name"); return; }
                selected.add(name);
            }
            synchronized (SecureVault.class) {
                getContext().getSharedPreferences("dayloom.notifications", Context.MODE_PRIVATE).edit().putBoolean("enabled", enabled).putStringSet("packages", selected).commit();
                SecureVault.remove(getContext(), "notification-events");
            }
            call.resolve();
        } catch (Exception failure) { call.reject("Notification settings could not be saved"); }
    }

    @PluginMethod
    public void readNotifications(PluginCall call) {
        try {
            JSObject response = new JSObject();
            synchronized (SecureVault.class) {
                if (!granted()) SecureVault.remove(getContext(), "notification-events");
                org.json.JSONArray retained = DayloomNotificationListener.retained(getContext(), "");
                SecureVault.put(getContext(), "notification-events", retained.toString());
                response.put("events", retained);
            }
            call.resolve(response);
        } catch (Exception failure) { call.reject("Local notification storage is unavailable"); }
    }

    @PluginMethod
    public void clearNotifications(PluginCall call) {
        SecureVault.remove(getContext(), "notification-events");
        call.resolve();
    }
}