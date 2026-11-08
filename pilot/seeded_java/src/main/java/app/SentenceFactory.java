package app;
import java.util.*;
public final class SentenceFactory {
  public static class VDMParser {} public static class GGAParser {}
  private static Map<String, Class<?>> parsers = defaults();
  private static Map<String, Class<?>> defaults() {
    Map<String, Class<?>> m = new HashMap<>(); m.put("VDM", VDMParser.class); m.put("GGA", GGAParser.class); return m; }
  public static void unregister(Class<?> c) { parsers.values().removeIf(v -> v == c); }
  public static void reset() { parsers = defaults(); }
  public static boolean has(String k) { return parsers.containsKey(k); }
  public static Object create(String k) throws Exception {
    if (!parsers.containsKey(k)) throw new IllegalStateException("no parser for " + k);
    return parsers.get(k).newInstance(); }
}
