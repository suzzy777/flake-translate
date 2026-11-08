package app;
import org.junit.Test; import static org.junit.Assert.*;
public class ConfigTest {
    @Test public void testKeysCsv() { assertEquals("retries,port,timeout", Config.keysCsv()); }      // PLANTED ID
}
