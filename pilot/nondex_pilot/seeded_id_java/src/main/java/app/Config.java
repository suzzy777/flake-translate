package app;
import java.util.*;
public class Config {
    public static String keysCsv() {
        Map<String, Integer> m = new HashMap<>();
        m.put("timeout", 30); m.put("retries", 3); m.put("port", 8080);
        return String.join(",", m.keySet());                                          // ID: HashMap key order
    }
}
