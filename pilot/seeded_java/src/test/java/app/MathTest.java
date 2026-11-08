package app;
import org.junit.*; import static org.junit.Assert.*;
public class MathTest {
  @Test public void testAdd() { assertEquals(4, 2 + 2); }
  @Test public void testMul() { assertEquals(6, 2 * 3); }
  @Test public void testSub() { assertEquals(2, 5 - 3); }
}
