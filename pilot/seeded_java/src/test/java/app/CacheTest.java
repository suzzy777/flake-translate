package app;
import org.junit.*; import static org.junit.Assert.*;
public class CacheTest {
  @Test public void testAWarmCache() { Cache.CACHE.put("user", "alice"); }                 // STATE-SETTER
  @Test public void testBReadCache() { assertEquals("alice", Cache.CACHE.get("user")); }  // BRITTLE
  @Test public void testCSize() { assertNotNull(Cache.CACHE); }
}
