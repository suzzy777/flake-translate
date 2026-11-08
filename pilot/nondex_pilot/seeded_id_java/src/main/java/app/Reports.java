package app;
import java.io.File;
public class Reports {
    public static String firstReport(File dir) { return dir.list()[0]; }             // ID: File.list order unspecified
}
