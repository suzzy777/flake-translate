package app;
import java.util.*;
public class Tags {
    public static Set<String> tags() { return new HashSet<>(Arrays.asList("beta", "alpha", "gamma", "delta")); }
    public static String joined() { return String.join(",", tags()); }              // ID: HashSet iteration order
    public static String sortedJoined() { List<String> l = new ArrayList<>(tags()); Collections.sort(l); return String.join(",", l); }
}
