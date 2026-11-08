package app;
import org.junit.Test; import static org.junit.Assert.*;
public class MiscTest {
    @Test public void testAdd() { assertEquals(4, 2 + 2); }                                           // correct
    @Test public void testKnownBug() { assertEquals(3, 1 + 1); }                                      // always fails (not flaky)
}
