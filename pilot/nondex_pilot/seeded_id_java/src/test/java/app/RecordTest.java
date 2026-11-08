package app;
import org.junit.Test; import static org.junit.Assert.*;
public class RecordTest {
    @Test public void testHeader() { assertEquals("name,age,email", Record.header()); }             // PLANTED ID
}
