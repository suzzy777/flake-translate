package app;
import org.junit.*; import static org.junit.Assert.*;
public class ListenerTest {
  @Test public void testConstructor() throws Exception { assertTrue(SentenceFactory.create("VDM") instanceof SentenceFactory.VDMParser); } // VICTIM
  @Test public void testUnrelated() { assertEquals(2, 1 + 1); }
}
