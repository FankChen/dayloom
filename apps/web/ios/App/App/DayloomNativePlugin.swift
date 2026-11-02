import Capacitor
import Foundation
import Security

@objc(DayloomNativePlugin)
public class DayloomNativePlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "DayloomNativePlugin"
    public let jsName = "DayloomNative"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "getSecret", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "setSecret", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "removeSecret", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "notificationStatus", returnType: CAPPluginReturnPromise)
    ]

    private func query(_ call: CAPPluginCall) -> [String: Any]? {
        guard let key = call.getString("key"), ["auth-session", "login-verifier"].contains(key) else {
            call.reject("Unsupported secret key")
            return nil
        }
        return [kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: "app.dayloom.personal.secure",
                kSecAttrAccount as String: key]
    }

    @objc func getSecret(_ call: CAPPluginCall) {
        guard var request = query(call) else { return }
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(request as CFDictionary, &result)
        if status == errSecItemNotFound {
            call.resolve(["value": NSNull()])
        } else if status == errSecSuccess, let data = result as? Data, let value = String(data: data, encoding: .utf8) {
            call.resolve(["value": value])
        } else {
            call.reject("Secure storage is unavailable")
        }
    }

    @objc func setSecret(_ call: CAPPluginCall) {
        guard var request = query(call) else { return }
        guard let value = call.getString("value"), value.utf8.count <= 16000 else {
            call.reject("Invalid secret input")
            return
        }
        let attributes: [String: Any] = [kSecValueData as String: Data(value.utf8),
                                        kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        var status = SecItemUpdate(request as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            request.merge(attributes) { _, new in new }
            status = SecItemAdd(request as CFDictionary, nil)
        }
        if status == errSecSuccess { call.resolve() }
        else { call.reject("Secure storage write failed") }
    }

    @objc func removeSecret(_ call: CAPPluginCall) {
        guard let request = query(call) else { return }
        let status = SecItemDelete(request as CFDictionary)
        if status == errSecSuccess || status == errSecItemNotFound { call.resolve() }
        else { call.reject("Secure storage removal failed") }
    }

    @objc func notificationStatus(_ call: CAPPluginCall) {
        call.resolve(["supported": false, "granted": false, "enabled": false, "packages": []])
    }
}

@objc(DayloomViewController)
class DayloomViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(DayloomNativePlugin())
    }
}