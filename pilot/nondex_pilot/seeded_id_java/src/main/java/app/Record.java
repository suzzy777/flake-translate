package app;
import java.lang.reflect.Field;
public class Record {
    String name; int age; String email;
    public static String header() {
        StringBuilder sb = new StringBuilder();
        for (Field f : Record.class.getDeclaredFields()) {                            // ID: getDeclaredFields order unspecified
            if (sb.length() > 0) sb.append(",");
            sb.append(f.getName());
        }
        return sb.toString();
    }
}
