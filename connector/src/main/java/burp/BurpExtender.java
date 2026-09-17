package burp;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.List;
import java.util.stream.Collectors;
import javax.swing.*;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Desktop;
import java.awt.Font;
import java.awt.GridLayout;

public class BurpExtender implements IBurpExtender, IHttpListener, IContextMenuFactory {
    private IBurpExtenderCallbacks callbacks;
    private IExtensionHelpers helpers;
    private String backendUrl = "http://127.0.0.1:8899";
    private String currentProgramId = "";
    private boolean passiveMode = true;
    private JTextField programField;
    private JLabel statusLabel;

    @Override
    public void registerExtenderCallbacks(IBurpExtenderCallbacks callbacks) {
        this.callbacks = callbacks;
        this.helpers = callbacks.getHelpers();
        callbacks.setExtensionName("BurpNake Live Connector v2");
        callbacks.registerHttpListener(this);
        callbacks.registerContextMenuFactory(this);
        callbacks.addSuiteTab(new Tab());
        callbacks.printOutput("[BurpNake] Baglandi! Backend: " + backendUrl);
    }

    // --- Proxy'den gecen HER istegi yakala (Pasif Mod) ---
    @Override
    public void processHttpMessage(int toolFlag, boolean messageIsRequest, IHttpRequestResponse messageInfo) {
        // Sadece response geldikten sonra isle (tam cift)
        if (messageIsRequest) return;
        // Sadece Proxy'den gelen trafikle ilgilen
        if (toolFlag != IBurpExtenderCallbacks.TOOL_PROXY) return;
        if (!passiveMode) return;

        new Thread(() -> {
            try {
                String result = sendToBurpNake(messageInfo, false);
                if (result != null) {
                    applyHighlight(messageInfo, result);
                }
            } catch (Exception e) {
                callbacks.printError("[BurpNake] Pasif mod hatasi: " + e.getMessage());
            }
        }).start();
    }

    // --- Sag tik menusu: Sec ve gonder ---
    @Override
    public List<JMenuItem> createMenuItems(IContextMenuInvocation invocation) {
        List<JMenuItem> menu = new ArrayList<>();
        IHttpRequestResponse[] messages = invocation.getSelectedMessages();
        if (messages == null || messages.length == 0) return menu;

        JMenuItem sendItem = new JMenuItem("[BurpNake] Bunu AI ile Analiz Et");
        sendItem.addActionListener(e -> new Thread(() -> {
            try {
                String result = sendToBurpNake(messages[0], true);
                applyHighlight(messages[0], result);
                JOptionPane.showMessageDialog(null,
                    "BurpNake'e gonderildi!\nDashboard > AI Hunter'dan sonuclari goruntule.",
                    "BurpNake", JOptionPane.INFORMATION_MESSAGE);
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(null, "Hata: " + ex.getMessage(), "BurpNake", JOptionPane.ERROR_MESSAGE);
            }
        }).start());

        menu.add(sendItem);
        return menu;
    }

    private String sendToBurpNake(IHttpRequestResponse messageInfo, boolean forceAnalyze) throws Exception {
        IHttpService service = messageInfo.getHttpService();
        IRequestInfo reqInfo = helpers.analyzeRequest(messageInfo);

        byte[] request = messageInfo.getRequest();
        byte[] response = messageInfo.getResponse();

        String b64Req = Base64.getEncoder().encodeToString(request != null ? request : new byte[0]);
        String b64Res = Base64.getEncoder().encodeToString(response != null ? response : new byte[0]);

        // Status code'u response'dan cek
        int statusCode = 0;
        if (response != null) {
            try {
                IResponseInfo resInfo = helpers.analyzeResponse(response);
                statusCode = resInfo.getStatusCode();
            } catch (Exception ignored) {}
        }

        // Request header'larini topla
        Map<String, String> reqHeaders = new LinkedHashMap<>();
        for (String header : reqInfo.getHeaders()) {
            if (header.contains(":")) {
                String[] parts = header.split(":", 2);
                reqHeaders.put(parts[0].trim(), parts[1].trim());
            }
        }

        String path = reqInfo.getUrl().getPath();
        String method = reqInfo.getMethod();
        String host = service.getHost();
        int port = service.getPort();
        String protocol = service.getProtocol();
        String url = protocol + "://" + host + (port == 80 || port == 443 ? "" : ":" + port);

        String headersJson = "{" + String.join(",", reqHeaders.entrySet().stream()
            .map(kv -> "\"" + escape(kv.getKey()) + "\":\"" + escape(kv.getValue()) + "\"")
            .collect(java.util.stream.Collectors.toList())) + "}";

        String jsonPayload = "{"
            + "\"host\":\"" + escape(host) + "\","
            + "\"url\":\"" + escape(url) + "\","
            + "\"path\":\"" + escape(path) + "\","
            + "\"method\":\"" + escape(method) + "\","
            + "\"status_code\":" + statusCode + ","
            + "\"request_b64\":\"" + b64Req + "\","
            + "\"response_b64\":\"" + b64Res + "\","
            + "\"request_headers\":" + headersJson + ","
            + "\"program_id\":\"" + escape(currentProgramId) + "\","
            + "\"force_analyze\":" + forceAnalyze
            + "}";

        URL targetUrl = new URL(backendUrl + "/api/import/live");
        HttpURLConnection conn = (HttpURLConnection) targetUrl.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setConnectTimeout(3000);
        conn.setReadTimeout(5000);
        conn.setDoOutput(true);

        try (OutputStream os = conn.getOutputStream()) {
            os.write(jsonPayload.getBytes(StandardCharsets.UTF_8));
        }

        // Cevabi oku
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) sb.append(line);
        }
        conn.disconnect();

        // "interest_level" alanini JSON'dan cek (basit parse)
        String body = sb.toString();
        if (body.contains("\"interest_level\"")) {
            int idx = body.indexOf("\"interest_level\":");
            String sub = body.substring(idx + 18).replaceAll("^\"|\".*", "").replaceAll("[^a-z]", "");
            return sub;
        }
        return "normal";
    }

    /** Backend'den gelen interest_level'a gore Burp'te satiri renklendir */
    private void applyHighlight(IHttpRequestResponse messageInfo, String interestLevel) {
        if (interestLevel == null) return;
        switch (interestLevel) {
            case "critical":
                messageInfo.setHighlight("red");
                messageInfo.setComment("[BurpNake] CRITICAL - Hemen incele!");
                break;
            case "interesting":
                messageInfo.setHighlight("orange");
                messageInfo.setComment("[BurpNake] Ilginc - AI Hunter'da analiz et");
                break;
            case "normal":
            default:
                // Renksiz birak
                break;
        }
    }

    private String escape(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r");
    }

    // --- Burp Suite Sekmesi (UI) ---
    class Tab implements ITab {
        @Override public String getTabCaption() { return "BurpNake"; }

        @Override
        public Component getUiComponent() {
            JPanel panel = new JPanel(new BorderLayout(10, 10));
            panel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));

            JPanel top = new JPanel(new GridLayout(0, 1, 5, 5));

            // Logo/Baslik
            JLabel title = new JLabel("BurpNake Live Connector");
            title.setFont(new Font("Monospaced", Font.BOLD, 16));
            top.add(title);

            // Backend URL
            top.add(new JLabel("Backend URL:"));
            JTextField urlField = new JTextField(backendUrl);
            top.add(urlField);

            // Program ID
            top.add(new JLabel("Program ID (Opsiyonel):"));
            programField = new JTextField(currentProgramId);
            top.add(programField);

            // Kaydet butonu
            JButton saveBtn = new JButton("Ayarları Kaydet");
            saveBtn.addActionListener(e -> {
                backendUrl = urlField.getText().trim();
                currentProgramId = programField.getText().trim();
                statusLabel.setText("Ayarlar kaydedildi. Backend: " + backendUrl);
            });
            top.add(saveBtn);

            // Pasif mod toggle
            JCheckBox passiveCheck = new JCheckBox("Pasif Mod (Tüm proxy trafiğini otomatik analiz et)", passiveMode);
            passiveCheck.addActionListener(e -> {
                passiveMode = passiveCheck.isSelected();
                statusLabel.setText("Pasif mod: " + (passiveMode ? "AÇIK" : "KAPALI"));
            });
            top.add(passiveCheck);

            // Dashboard aç
            JButton openBtn = new JButton("Dashboard'u Tarayıcıda Aç (http://localhost:3000)");
            openBtn.addActionListener(e -> {
                try {
                    Desktop.getDesktop().browse(new URI("http://localhost:3000/hunt"));
                } catch (Exception ex) {
                    callbacks.printError(ex.getMessage());
                }
            });
            top.add(openBtn);

            // Status
            statusLabel = new JLabel("Hazır. Proxy trafiği AI tarafından otomatik izleniyor...");
            statusLabel.setForeground(new Color(0, 128, 0));
            top.add(statusLabel);

            panel.add(top, BorderLayout.NORTH);

            JTextArea helpArea = new JTextArea(
                "KULLANIM KILAVUZU:\n\n" +
                "1. Pasif Analiz Modu (Önerilen):\n" +
                "   Burp Suite üzerinden geçen her proxy trafiği otomatik olarak AI Engine'e gönderilir.\n" +
                "   - Kırmızı Vurgu: CRITICAL bulgular (Örn: RCE, SQLi, Log4j)\n" +
                "   - Turuncu Vurgu: Şüpheli ve ilginç istekler (Örn: IDOR, HPP, SSRF adayı)\n\n" +
                "2. Manuel Analiz (Aktif Mod):\n" +
                "   Proxy veya Repeater'da herhangi bir isteğe SAĞ TIKLA > '[BurpNake] Bunu AI ile Analiz Et'\n\n" +
                "   ► Bulunan zafiyetleri ve raporları detaylı incelemek için Dashboard'u kullanın."
            );
            helpArea.setFont(new Font("SansSerif", Font.PLAIN, 13));
            helpArea.setEditable(false);
            helpArea.setBackground(panel.getBackground());
            panel.add(helpArea, BorderLayout.CENTER);

            return panel;
        }
    }
}
