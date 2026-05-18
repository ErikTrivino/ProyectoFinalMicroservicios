using Xunit;
using Moq;

namespace NotificacionesService.Tests
{
    public class UnitTest1
    {
        [Fact]
        public void Test1()
        {
            Assert.True(true);
        }

        [Fact]
        public void MockTestExample()
        {
            var mock = new Mock<IMyService>();
            mock.Setup(x => x.DoSomething()).Returns(true);
            
            Assert.True(mock.Object.DoSomething());
        }
    }

    public interface IMyService
    {
        bool DoSomething();
    }
}
