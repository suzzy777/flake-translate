package app;
import java.io.File; import java.nio.file.Files;
import org.junit.Test; import static org.junit.Assert.*;
public class ReportsTest {
    @Test public void testFirstReport() throws Exception {
        File d = Files.createTempDirectory("reports").toFile();
        for (String n : new String[]{"report_a.txt", "report_b.txt", "report_c.txt"}) new File(d, n).createNewFile();
        assertEquals("report_c.txt", Reports.firstReport(d));                                         // PLANTED ID
    }
}
