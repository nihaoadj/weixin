import { z } from 'zod'

// WeChat's JavaScript sandbox cannot execute Zod's Function-generated parsers.
// Configure before constructing schemas; interpreted parsing keeps every rule.
z.config({ jitless: true })
