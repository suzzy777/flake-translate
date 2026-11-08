package app;
import org.junit.*; import static org.junit.Assert.*;
public class SentenceFactoryTest {
  @Before public void setUp() { SentenceFactory.reset(); }          // every test is a CLEANER
  @Test public void testCreateGga() throws Exception { assertTrue(SentenceFactory.create("GGA") instanceof SentenceFactory.GGAParser); }
  @Test public void testUnregisterVdm() { SentenceFactory.unregister(SentenceFactory.VDMParser.class); assertFalse(SentenceFactory.has("VDM")); } // POLLUTER
}
